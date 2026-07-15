#!/usr/bin/env python3
"""
Quince.com Lab-Grown Diamond jewelry scraper.

Scrapes every product from a Quince listing page, and for each product scrapes
EVERY variant (each carat size is its own URL like `...---2ctw`, each metal
color is a `?color=` query param). For every variant it saves:

  - every gallery photo (highest resolution available) and any videos
  - every "details" accordion section, section by section, as text + JSON
  - the brand price-comparison section ("Compare to" widget)
  - structured data (name, price, rating, SKU, description) from JSON-LD
  - a raw HTML snapshot of the page (so nothing is ever lost)

Output layout (default root is D:\\Quince_LabGrownDiamond on Windows):

  <out>/
    _catalog/
      products_index.csv        master index of every variant scraped
      products_index.json
      listing_snapshot.html     raw listing page
      listing_tiles.json        product tiles found on the listing
      scrape_log.txt
      failures.json             anything that failed, with reasons
    <Product Family Name>/
      family_info.json          all discovered variants of this product
      <carat, e.g. 2ctw>/
        <color, e.g. white-gold>/
          photos/               01_ab12cd34.jpg, 02_...  (deduped, max-res)
          photos_manifest.json  filename -> source URL
          details.txt           section-wise details, human readable
          details.json          structured: sections, price, rating, options
          comparison.txt        the brand comparison section
          comparison.json
          page.html             raw HTML snapshot of this variant page
          _done.json            marker used to resume interrupted runs

Usage (Windows, writing to the D: drive):
  python scrape_quince.py --out "D:\\Quince_LabGrownDiamond"

Usage (Linux/remote session):
  python scrape_quince.py --out ./scraped_data

Requires: pip install playwright && playwright install chromium
"""

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import time
import traceback
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright, Error as PWError

BASE = "https://www.quince.com"
DEFAULT_LISTING = (
    "https://www.quince.com/shop/jewelry?filter=materials%3DLab%2520Grown%2520Diamond"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# slugs look like: /women/14k-gold-lab-grown-diamond-tennis-bracelet---2ctw
CTW_RE = re.compile(r"---([0-9]+(?:-[0-9]+)?(?:\.[0-9]+)?)\s*ctw", re.I)
PRODUCT_PATH_RE = re.compile(r"^/(women|men|kids|gifts|home)/[a-z0-9][a-z0-9\-]*$", re.I)

log = logging.getLogger("quince")


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------

def sanitize_name(name: str, max_len: int = 90) -> str:
    """Make a string safe as a Windows/macOS/Linux folder name."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return (name[:max_len].strip(" .")) or "unnamed"


def normalize_variant_url(url: str) -> str:
    """Canonical key for a variant: path + sorted color/size params only."""
    p = urllib.parse.urlsplit(url)
    q = urllib.parse.parse_qs(p.query)
    keep = {k: v for k, v in q.items() if k.lower() in ("color", "size", "length")}
    query = urllib.parse.urlencode(sorted(keep.items()), doseq=True)
    return urllib.parse.urlunsplit(
        (p.scheme or "https", p.netloc or "www.quince.com", p.path.rstrip("/"), query, ""))


def family_key(url: str) -> str:
    """Product family = slug with the trailing ---<N>ctw removed, no query."""
    path = urllib.parse.urlsplit(url).path.rstrip("/")
    return re.sub(r"---[0-9][0-9.\-]*\s*ctw$", "", path, flags=re.I)


def carat_label(url: str) -> str:
    m = CTW_RE.search(urllib.parse.urlsplit(url).path)
    return (m.group(1) + "ctw") if m else "single-size"


def color_label(url: str) -> str:
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    vals = q.get("color") or q.get("Color")
    return vals[0] if vals else "default-color"


def clean_text(s: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", (s or "").replace("\r", ""))).strip()


def pick_largest_from_srcset(srcset: str) -> str:
    """Return the URL with the largest width descriptor from a srcset."""
    best_url, best_w = "", -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = bits[0]
        w = 0
        if len(bits) > 1:
            m = re.match(r"([0-9]+(?:\.[0-9]+)?)[wx]", bits[1])
            if m:
                w = float(m.group(1))
        if w > best_w:
            best_w, best_url = w, url
    return best_url


def absolutize(url: str, base: str = BASE + "/") -> str:
    return urllib.parse.urljoin(base, url)


def upsize_image_url(url: str, base: str = BASE + "/") -> str:
    """Rewrite CDN/image-proxy URLs to request the highest resolution."""
    url = absolutize(url, base)
    parts = urllib.parse.urlsplit(url)
    # Next.js image proxy: /_next/image?url=<encoded original>&w=640&q=75
    if "/_next/image" in parts.path:
        q = urllib.parse.parse_qs(parts.query)
        inner = q.get("url", [""])[0]
        if inner.startswith("http"):
            return upsize_image_url(inner)
        if inner:  # relative inner URL: keep proxy but ask for max width
            q["w"] = ["3840"]
            q["q"] = ["90"]
            return urllib.parse.urlunsplit(
                parts._replace(query=urllib.parse.urlencode(q, doseq=True)))
    # imgix / generic resize params: bump width, drop crops
    q = urllib.parse.parse_qs(parts.query)
    if any(k in q for k in ("w", "width")):
        for k in ("w", "width"):
            if k in q:
                q[k] = ["2400"]
        for k in ("h", "height", "fit", "crop", "rect"):
            q.pop(k, None)
        return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q, doseq=True)))
    return url


def image_dedup_key(url: str) -> str:
    """Two URLs that differ only by resize params are the same image."""
    parts = urllib.parse.urlsplit(url)
    if "/_next/image" in parts.path:
        inner = urllib.parse.parse_qs(parts.query).get("url", [""])[0]
        if inner:
            return image_dedup_key(absolutize(inner))
    return parts.netloc + parts.path


def looks_like_product_image(url: str) -> bool:
    u = url.lower()
    if u.startswith("data:"):
        return False
    bad = ("logo", "icon", "sprite", "flag", "favicon", "badge", "payment",
           "avatar", "placeholder.", "loading.")
    return not any(b in u for b in bad)


def guess_ext(url: str, content_type: str) -> str:
    ct = (content_type or "").lower()
    for mime, ext in (("jpeg", ".jpg"), ("png", ".png"), ("webp", ".webp"),
                      ("avif", ".avif"), ("gif", ".gif"), ("mp4", ".mp4")):
        if mime in ct:
            return ext
    m = re.search(r"\.(jpe?g|png|webp|avif|gif|mp4|mov)(?:$|\?)", url.lower())
    if m:
        return "." + m.group(1).replace("jpeg", "jpg")
    return ".jpg"


# ----------------------------------------------------------------------------
# scraper
# ----------------------------------------------------------------------------

class QuinceScraper:
    def __init__(self, args):
        self.args = args
        self.out = Path(args.out)
        self.catalog_dir = self.out / "_catalog"
        self.catalog_dir.mkdir(parents=True, exist_ok=True)
        self.index_rows = []
        self.failures = []
        self.visited_variants = set()

    # -- lifecycle -----------------------------------------------------------

    def run(self):
        with sync_playwright() as p:
            launch_kw = {"headless": not self.args.headed}
            if self.args.chromium_path:
                launch_kw["executable_path"] = self.args.chromium_path
            browser = p.chromium.launch(**launch_kw)
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1440, "height": 2000},
                locale="en-US",
            )
            context.set_default_timeout(self.args.timeout * 1000)
            page = context.new_page()
            try:
                product_urls = self.get_product_urls(page)
                log.info("=== %d product tiles to scrape ===", len(product_urls))
                for i, url in enumerate(product_urls, 1):
                    if self.args.max_products and i > self.args.max_products:
                        log.info("Reached --max-products=%d, stopping.", self.args.max_products)
                        break
                    log.info("[%d/%d] product family: %s", i, len(product_urls), url)
                    try:
                        self.scrape_family(page, url)
                    except Exception as e:  # keep going: one bad product must not kill the run
                        log.error("FAMILY FAILED %s: %s", url, e)
                        log.debug(traceback.format_exc())
                        self.failures.append({"stage": "family", "url": url, "error": str(e)})
                    self.write_index()
            finally:
                self.write_index()
                context.close()
                browser.close()
        log.info("DONE. %d variants scraped, %d failures. Output: %s",
                 len(self.index_rows), len(self.failures), self.out)

    # -- listing -------------------------------------------------------------

    def get_product_urls(self, page):
        if self.args.products_file:
            urls = [l.strip() for l in Path(self.args.products_file).read_text(
                encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
            log.info("Loaded %d product URLs from %s", len(urls), self.args.products_file)
            return urls
        return self.discover_from_listing(page)

    def discover_from_listing(self, page):
        log.info("Opening listing: %s", self.args.listing_url)
        self.goto(page, self.args.listing_url)
        self.dismiss_popups(page)

        stable_rounds, last_count = 0, -1
        for _ in range(120):  # scroll/"load more" until the grid stops growing
            page.mouse.wheel(0, 20000)
            page.wait_for_timeout(1500)
            for pat in (r"load more", r"show more", r"view more"):
                try:
                    btn = page.get_by_role("button", name=re.compile(pat, re.I)).first
                    if btn.is_visible(timeout=500):
                        btn.click()
                        page.wait_for_timeout(1500)
                except Exception:
                    pass
            count = len(self.listing_tiles(page))
            if count == last_count:
                stable_rounds += 1
                if stable_rounds >= 4:
                    break
            else:
                stable_rounds, last_count = 0, count

        tiles = self.listing_tiles(page)
        (self.catalog_dir / "listing_snapshot.html").write_text(page.content(), encoding="utf-8")
        (self.catalog_dir / "listing_tiles.json").write_text(
            json.dumps(tiles, indent=2, ensure_ascii=False), encoding="utf-8")

        seen_families, urls = set(), []
        for t in tiles:
            fk = family_key(t["url"])
            if fk not in seen_families:
                seen_families.add(fk)
                urls.append(t["url"])
        log.info("Listing: %d tiles -> %d unique product families", len(tiles), len(urls))
        if not urls:
            raise RuntimeError(
                "No product tiles found on the listing page — the page may be "
                "blocked or its markup changed. See _catalog/listing_snapshot.html")
        return urls

    def listing_tiles(self, page):
        """All product links on the listing page (anchors that contain an image)."""
        tiles = page.evaluate(
            """() => {
                const out = [];
                for (const a of document.querySelectorAll('a[href]')) {
                    if (a.closest('footer, nav, header')) continue;
                    const href = a.getAttribute('href') || '';
                    const path = href.split('?')[0];
                    if (!/^\\/(women|men|kids|gifts|home)\\/[a-z0-9][a-z0-9\\-]*$/i.test(path)) continue;
                    const img = a.querySelector('img');
                    if (!img) continue;
                    const w = img.getBoundingClientRect().width || img.width || 0;
                    if (w && w < 100) continue;  // logos/badges, not product tiles
                    const name = (a.getAttribute('aria-label') || a.innerText || '')
                        .split('\\n').map(s => s.trim()).filter(Boolean)[0] || '';
                    const priceM = (a.innerText || '').match(/\\$[0-9][0-9,.]*/);
                    out.push({url: href, name, price: priceM ? priceM[0] : ''});
                }
                return out;
            }"""
        )
        seen, uniq = set(), []
        for t in tiles:
            t["url"] = absolutize(t["url"], page.url)
            key = normalize_variant_url(t["url"])
            if key not in seen:
                seen.add(key)
                uniq.append(t)
        return uniq

    # -- product family ------------------------------------------------------

    def scrape_family(self, page, start_url):
        fk = family_key(start_url)
        queue = [normalize_variant_url(start_url)]
        family_dir = None
        family_variants = []

        while queue:
            url = queue.pop(0)
            if url in self.visited_variants:
                continue
            self.visited_variants.add(url)
            if len(family_variants) >= self.args.max_variants_per_product:
                log.warning("Variant cap (%d) hit for %s; skipping the rest.",
                            self.args.max_variants_per_product, fk)
                break
            try:
                info = self.scrape_variant(page, url, fk, family_dir)
            except Exception as e:
                log.error("VARIANT FAILED %s: %s", url, e)
                log.debug(traceback.format_exc())
                self.failures.append({"stage": "variant", "url": url, "error": str(e)})
                continue
            if family_dir is None:
                family_dir = info["family_dir"]
            if info["summary"]:
                family_variants.append(info["summary"])
            # newly discovered sibling variants (other carats / colors)
            for sib in info["sibling_urls"]:
                if sib not in self.visited_variants and sib not in queue:
                    queue.append(sib)
            time.sleep(self.args.delay)

        if family_dir and family_variants:
            (Path(family_dir) / "family_info.json").write_text(
                json.dumps({"family": fk, "variants": family_variants},
                           indent=2, ensure_ascii=False), encoding="utf-8")

    # -- one variant page ----------------------------------------------------

    def scrape_variant(self, page, url, fk, family_dir):
        self.goto(page, url)
        self.dismiss_popups(page)
        page.wait_for_timeout(800)
        self.lazy_scroll(page)

        ld = self.extract_json_ld(page)
        title = ld.get("name") or self.first_text(page, "h1") or Path(
            urllib.parse.urlsplit(url).path).name
        family_name = sanitize_name(re.sub(r"\s*[-–—]*\s*[0-9][0-9.]*\s*ctw\s*$", "",
                                           title, flags=re.I)) or sanitize_name(title)
        if family_dir is None:
            family_dir = self.out / family_name
        family_dir = Path(family_dir)
        vdir = family_dir / sanitize_name(carat_label(url)) / sanitize_name(color_label(url))
        done_marker = vdir / "_done.json"

        summary = {
            "product_family": family_name, "carat": carat_label(url),
            "color": color_label(url), "url": url, "title": title,
        }

        siblings = self.discover_sibling_variants(page, fk)

        # A URL without ?color= shows the same content as one of the explicit
        # color variants — skip it when explicit colors exist (no duplicates).
        cur = urllib.parse.urlsplit(url)
        if "color" not in urllib.parse.parse_qs(cur.query):
            has_explicit_colors = any(
                urllib.parse.urlsplit(s).path == cur.path
                and "color" in urllib.parse.parse_qs(urllib.parse.urlsplit(s).query)
                for s in siblings)
            if has_explicit_colors:
                log.info("  %s has explicit color variants; scraping those instead "
                         "of the generic page", carat_label(url))
                return {"family_dir": family_dir, "summary": None,
                        "sibling_urls": siblings}

        if done_marker.exists() and not self.args.force:
            log.info("  already scraped, skipping: %s / %s / %s",
                     family_name, summary["carat"], summary["color"])
            try:
                prev = json.loads(done_marker.read_text(encoding="utf-8"))
                summary.update({k: prev.get(k) for k in
                                ("price", "currency", "rating", "review_count",
                                 "num_photos") if k in prev})
            except Exception:
                pass
            self.index_rows.append({**summary, "folder": str(vdir)})
            return {"family_dir": family_dir, "summary": summary, "sibling_urls": siblings}

        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "page.html").write_text(page.content(), encoding="utf-8")

        sections = self.extract_sections(page)
        comparison = self.extract_comparison(page)
        options = self.extract_option_groups(page)
        price, currency = self.extract_price(page, ld)
        rating, review_count = self.extract_rating(ld, page)

        details = {
            "url": url, "title": title, "carat": summary["carat"],
            "color": summary["color"], "price": price, "currency": currency,
            "rating": rating, "review_count": review_count,
            "sku": ld.get("sku"), "brand": (ld.get("brand") or {}).get("name")
                if isinstance(ld.get("brand"), dict) else ld.get("brand"),
            "description": clean_text(ld.get("description") or ""),
            "option_groups": options, "sections": sections,
            "sibling_variant_urls": siblings, "json_ld": ld,
        }
        (vdir / "details.json").write_text(
            json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
        (vdir / "details.txt").write_text(
            self.render_details_txt(details), encoding="utf-8")
        (vdir / "comparison.json").write_text(
            json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
        (vdir / "comparison.txt").write_text(
            comparison.get("text") or "No comparison section found on this page.",
            encoding="utf-8")

        num_photos = 0
        if not self.args.skip_images:
            media = self.collect_media(page, ld)
            num_photos = self.download_media(page, media, vdir / "photos")

        summary.update({"price": price, "currency": currency, "rating": rating,
                        "review_count": review_count, "num_photos": num_photos})
        self.index_rows.append({**summary, "folder": str(vdir)})
        done_marker.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                               encoding="utf-8")
        log.info("  saved: %s | %s | %s | price=%s | photos=%d | sections=%d",
                 family_name, summary["carat"], summary["color"], price,
                 num_photos, len(sections))
        return {"family_dir": family_dir, "summary": summary, "sibling_urls": siblings}

    # -- extraction pieces ---------------------------------------------------

    def discover_sibling_variants(self, page, fk):
        """Links on the PDP to other carat sizes / colors of the SAME product."""
        hrefs = page.evaluate(
            "() => Array.from(document.querySelectorAll('a[href]'))"
            ".map(a => a.getAttribute('href'))")
        out = []
        page_host = urllib.parse.urlsplit(page.url).netloc
        for h in hrefs or []:
            if not h:
                continue
            full = absolutize(h, page.url)
            p = urllib.parse.urlsplit(full)
            if p.netloc and p.netloc != page_host and "quince.com" not in p.netloc:
                continue
            if family_key(full) != fk:
                continue
            if not PRODUCT_PATH_RE.match(p.path.rstrip("/")) and not CTW_RE.search(p.path):
                continue
            out.append(normalize_variant_url(full))
        return sorted(set(out))

    def extract_json_ld(self, page):
        blocks = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'script[type=\"application/ld+json\"]')).map(s => s.textContent)")
        for raw in blocks or []:
            try:
                data = json.loads(raw)
            except Exception:
                continue
            candidates = data if isinstance(data, list) else [data]
            for c in candidates:
                if isinstance(c, dict) and c.get("@graph"):
                    candidates.extend(x for x in c["@graph"] if isinstance(x, dict))
                if isinstance(c, dict) and str(c.get("@type", "")).lower() == "product":
                    return c
        return {}

    def extract_price(self, page, ld):
        offers = ld.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = offers.get("price") or offers.get("lowPrice")
        currency = offers.get("priceCurrency") or "USD"
        if price:
            return str(price), currency
        # DOM fallback: first $-amount near the top of the buy box / h1
        txt = self.first_text(page, "main") or ""
        m = re.search(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{2})?)", txt)
        return (m.group(1).replace(",", "") if m else None), currency

    def extract_rating(self, ld, page):
        agg = ld.get("aggregateRating") or {}
        rating = agg.get("ratingValue")
        count = agg.get("reviewCount") or agg.get("ratingCount")
        return (str(rating) if rating is not None else None,
                str(count) if count is not None else None)

    def extract_option_groups(self, page):
        """Record every option/selector group visible in the buy box (carat,
        color, length, ring size, ...) with its choices, without clicking."""
        return page.evaluate(
            """() => {
                const groups = [];
                const seen = new Set();
                const sels = ['[role="radiogroup"]', 'fieldset', 'select',
                              '[class*="swatch" i]', '[class*="option" i]',
                              '[class*="variant" i]', '[class*="selector" i]'];
                for (const sel of sels) {
                    for (const el of document.querySelectorAll('main ' + sel)) {
                        if (el.closest('footer,nav')) continue;
                        const label = (el.querySelector('legend,label,[class*="label" i]')?.innerText
                                       || el.getAttribute('aria-label') || '').trim().slice(0, 80);
                        let opts = [];
                        if (el.tagName === 'SELECT') {
                            opts = Array.from(el.options).map(o => o.textContent.trim());
                        } else {
                            opts = Array.from(el.querySelectorAll(
                                'a,button,[role="radio"],input+label'))
                                .map(o => (o.getAttribute('aria-label') || o.innerText || '')
                                    .trim().replace(/\\s+/g, ' '))
                                .filter(t => t && t.length < 60);
                        }
                        opts = Array.from(new Set(opts));
                        if (opts.length < 2 || opts.length > 40) continue;
                        const key = label + '|' + opts.join(',');
                        if (seen.has(key)) continue;
                        seen.add(key);
                        groups.push({label, options: opts});
                    }
                }
                return groups.slice(0, 12);
            }"""
        )

    def extract_sections(self, page):
        """Expand and capture every details accordion / section on the PDP."""
        # expand collapsed accordions so their text is in the DOM
        for _ in range(2):
            buttons = page.query_selector_all(
                'main [aria-expanded="false"], main details:not([open]) > summary')
            if not buttons:
                break
            for b in buttons[:40]:
                try:
                    b.scroll_into_view_if_needed(timeout=2000)
                    b.click(timeout=2000)
                    page.wait_for_timeout(150)
                except Exception:
                    pass
        sections = page.evaluate(
            """() => {
                const out = [];
                const seen = new Set();
                const add = (title, text, html) => {
                    title = (title || '').trim().replace(/\\s+/g, ' ');
                    text = (text || '').trim();
                    if (!text || text.length < 3) return;
                    const key = title + '|' + text.slice(0, 120);
                    if (seen.has(key)) return;
                    seen.add(key);
                    out.push({title: title || '(untitled section)', text, html});
                };
                // 1) ARIA accordions: button[aria-expanded] + aria-controls panel
                for (const btn of document.querySelectorAll('main [aria-expanded]')) {
                    const id = btn.getAttribute('aria-controls');
                    let panel = id ? document.getElementById(id) : null;
                    if (!panel) {
                        panel = btn.closest('div,section,li')?.querySelector(
                            '[role="region"], [class*="panel" i], [class*="content" i]');
                    }
                    if (panel && panel.innerText && !panel.contains(btn)) {
                        add(btn.innerText, panel.innerText, panel.innerHTML.slice(0, 20000));
                    }
                }
                // 2) native <details>
                for (const d of document.querySelectorAll('main details')) {
                    const sum = d.querySelector('summary');
                    const clone = d.cloneNode(true);
                    clone.querySelector('summary')?.remove();
                    add(sum ? sum.innerText : '', clone.innerText,
                        clone.innerHTML.slice(0, 20000));
                }
                // 3) heading-led sections in the product info column
                for (const h of document.querySelectorAll('main h2, main h3')) {
                    const sec = h.parentElement;
                    if (!sec || sec.innerText.length > 3000) continue;
                    if (sec.querySelectorAll('h1,h2,h3').length > 1) continue;
                    const t = sec.innerText.replace(h.innerText, '').trim();
                    if (t) add(h.innerText, t, '');
                }
                return out;
            }"""
        )
        return sections or []

    def extract_comparison(self, page):
        """The Quince 'compare to other brands' widget: prices vs competitors."""
        data = page.evaluate(
            """() => {
                const nodes = Array.from(document.querySelectorAll('main *')).filter(el => {
                    const t = el.childElementCount <= 60 ? el.innerText : '';
                    return t && /compare|vs\\.?\\s|similar (item|brand)|traditional retail/i.test(t)
                        && /\\$\\s?[0-9]/.test(t) && t.length < 2500;
                });
                if (!nodes.length) return null;
                // smallest matching container = the actual widget
                nodes.sort((a, b) => a.innerText.length - b.innerText.length);
                let el = nodes[0];
                // climb while the parent still looks like the same compact widget
                while (el.parentElement &&
                       el.parentElement.innerText.length < el.innerText.length + 400 &&
                       el.parentElement.innerText.length < 2500) {
                    el = el.parentElement;
                }
                const text = el.innerText;
                const rows = [];
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                const priceRe = /^\\$\\s?([0-9][0-9,\\.]*)$/;
                for (let i = 0; i < lines.length; i++) {
                    // "Brand $1,234" on one line
                    const m = lines[i].match(/^(.+?)\\s+\\$\\s?([0-9][0-9,\\.]*)$/);
                    if (m) { rows.push({brand: m[1].trim(),
                                        price: m[2].replace(/,/g, '')}); continue; }
                    // "Brand" on one line, "$1,234" on the next
                    const p = lines[i + 1] ? lines[i + 1].match(priceRe) : null;
                    if (p && !priceRe.test(lines[i]) && lines[i].length < 60) {
                        rows.push({brand: lines[i], price: p[1].replace(/,/g, '')});
                        i++;
                    }
                }
                return {text, rows, html: el.innerHTML.slice(0, 30000)};
            }"""
        )
        return data or {"text": None, "rows": [], "html": None}

    # -- media ---------------------------------------------------------------

    def collect_media(self, page, ld):
        urls = []
        # JSON-LD image list is the most reliable full-gallery source
        ld_imgs = ld.get("image") or []
        if isinstance(ld_imgs, str):
            ld_imgs = [ld_imgs]
        for u in ld_imgs:
            if isinstance(u, dict):
                u = u.get("url") or u.get("contentUrl") or ""
            if u:
                urls.append(u)
        # every <img> / <source> in main content
        dom = page.evaluate(
            """() => {
                const urls = [];
                const root = document.querySelector('main') || document.body;
                for (const img of root.querySelectorAll('img')) {
                    const r = img.getBoundingClientRect();
                    if (img.width && img.width < 120 && r.width < 120) continue;
                    if (img.srcset) urls.push({srcset: img.srcset});
                    else if (img.currentSrc || img.src)
                        urls.push({src: img.currentSrc || img.src});
                }
                for (const s of root.querySelectorAll('picture source[srcset]'))
                    urls.push({srcset: s.srcset});
                for (const v of root.querySelectorAll('video'))
                    for (const src of [v.src, ...Array.from(
                            v.querySelectorAll('source')).map(x => x.src)])
                        if (src) urls.push({src, video: true});
                const og = document.querySelector('meta[property="og:image"]');
                if (og && og.content) urls.push({src: og.content});
                return urls;
            }"""
        )
        for item in dom or []:
            u = pick_largest_from_srcset(item["srcset"]) if item.get("srcset") else item.get("src")
            if u:
                urls.append(u)

        final, seen = [], set()
        for u in urls:
            u = absolutize(str(u), page.url)
            if not looks_like_product_image(u):
                continue
            key = image_dedup_key(u)
            if key in seen:
                continue
            seen.add(key)
            final.append(upsize_image_url(u, page.url))
        return final

    def download_media(self, page, urls, photos_dir: Path):
        photos_dir.mkdir(parents=True, exist_ok=True)
        manifest, saved = {}, 0
        for i, url in enumerate(urls, 1):
            body, ctype = None, ""
            for attempt, u in enumerate((url, re.sub(r"\?.*$", "", url)), 1):
                try:
                    resp = page.context.request.get(
                        u, timeout=45000, headers={"Referer": page.url})
                    if resp.ok:
                        body, ctype = resp.body(), resp.headers.get("content-type", "")
                        break
                except Exception as e:
                    log.debug("  image attempt %d failed %s: %s", attempt, u, e)
            if not body or len(body) < 2048:  # skip empty/1px responses
                self.failures.append({"stage": "image", "url": url, "error": "download failed"})
                continue
            name = f"{i:02d}_{hashlib.sha1(url.encode()).hexdigest()[:8]}{guess_ext(url, ctype)}"
            (photos_dir / name).write_bytes(body)
            manifest[name] = url
            saved += 1
        (photos_dir.parent / "photos_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return saved

    # -- navigation / page utilities -----------------------------------------

    def goto(self, page, url):
        last_err = None
        for attempt in range(1, 4):
            try:
                resp = page.goto(url, wait_until="domcontentloaded",
                                 timeout=self.args.timeout * 1000)
                if resp and resp.status == 404:
                    raise RuntimeError(f"HTTP 404 — page does not exist: {url}")
                if resp and resp.status in (403, 429, 503):
                    raise RuntimeError(f"HTTP {resp.status} (blocked/rate-limited)")
                page.wait_for_timeout(1200)
                return
            except Exception as e:
                last_err = e
                log.warning("goto attempt %d failed for %s: %s", attempt, url, e)
                page.wait_for_timeout(2500 * attempt)
        raise RuntimeError(f"Could not load {url}: {last_err}")

    def dismiss_popups(self, page):
        for pat in (r"^accept", r"accept all", r"^agree", r"^got it", r"^close",
                    r"no,? thanks", r"^continue", r"^×$", r"^x$"):
            try:
                btn = page.get_by_role("button", name=re.compile(pat, re.I)).first
                if btn.is_visible(timeout=400):
                    btn.click(timeout=1500)
                    page.wait_for_timeout(300)
            except Exception:
                pass
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    def lazy_scroll(self, page):
        """Scroll through the page so lazy-loaded gallery images populate."""
        try:
            height = page.evaluate("() => document.body.scrollHeight") or 4000
            step = 900
            for y in range(0, min(int(height), 30000), step):
                page.mouse.wheel(0, step)
                page.wait_for_timeout(120)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(400)
        except Exception:
            pass

    def first_text(self, page, selector):
        try:
            el = page.query_selector(selector)
            return el.inner_text().strip() if el else None
        except Exception:
            return None

    # -- output --------------------------------------------------------------

    def render_details_txt(self, d):
        lines = [
            d["title"] or "", "=" * max(10, len(d["title"] or "")), "",
            f"URL:          {d['url']}",
            f"Carat size:   {d['carat']}",
            f"Color/metal:  {d['color']}",
            f"Price:        {'$' + str(d['price']) if d['price'] else 'n/a'} {d['currency'] or ''}",
            f"Rating:       {d['rating'] or 'n/a'} ({d['review_count'] or '0'} reviews)",
            f"SKU:          {d['sku'] or 'n/a'}", "",
        ]
        if d.get("description"):
            lines += ["DESCRIPTION", "-" * 11, d["description"], ""]
        for g in d.get("option_groups") or []:
            label = g.get("label") or "Options"
            lines += [f"OPTIONS — {label}", "-" * (10 + len(label)),
                      ", ".join(g.get("options") or []), ""]
        for s in d.get("sections") or []:
            lines += [s["title"].upper(), "-" * max(3, len(s["title"])),
                      clean_text(s["text"]), ""]
        return "\n".join(lines)

    def write_index(self):
        cols = ["product_family", "title", "carat", "color", "price", "currency",
                "rating", "review_count", "num_photos", "url", "folder"]
        with open(self.catalog_dir / "products_index.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(self.index_rows)
        (self.catalog_dir / "products_index.json").write_text(
            json.dumps(self.index_rows, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.catalog_dir / "failures.json").write_text(
            json.dumps(self.failures, indent=2, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------------------------

def default_out():
    if sys.platform.startswith("win"):
        return r"D:\Quince_LabGrownDiamond"
    return "./quince_scraped_data"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=default_out(),
                    help=f"Output folder (default: {default_out()})")
    ap.add_argument("--listing-url", default=DEFAULT_LISTING,
                    help="Quince listing/collection URL to scrape")
    ap.add_argument("--products-file",
                    help="Optional text file of product URLs (one per line) to "
                         "scrape instead of discovering them from the listing")
    ap.add_argument("--max-products", type=int, default=0,
                    help="Only scrape the first N product families (0 = all)")
    ap.add_argument("--max-variants-per-product", type=int, default=60,
                    help="Safety cap on carat/color combinations per product")
    ap.add_argument("--delay", type=float, default=2.0,
                    help="Seconds to wait between product pages (be polite)")
    ap.add_argument("--timeout", type=int, default=45,
                    help="Per-navigation timeout in seconds")
    ap.add_argument("--skip-images", action="store_true",
                    help="Scrape text/details only, skip photo downloads")
    ap.add_argument("--force", action="store_true",
                    help="Re-scrape variants even if already downloaded")
    ap.add_argument("--headed", action="store_true",
                    help="Show the browser window (useful to watch it work)")
    ap.add_argument("--chromium-path", default=None,
                    help="Path to a Chromium executable (e.g. in a remote "
                         "session: /opt/pw-browsers/chromium)")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "_catalog").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(out / "_catalog" / "scrape_log.txt",
                                      encoding="utf-8")],
    )

    scraper = QuinceScraper(args)
    scraper.run()


if __name__ == "__main__":
    main()
