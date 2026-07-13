#!/usr/bin/env python3
"""Catalog scraper: product gallery photos + DETAILS screenshots from any
category/listing URL. Tuned for quince.com with generic fallbacks for other
standard e-commerce sites.

Scrapes the first N products (default 15) from a category page:
  * downloads every gallery photo at the highest available resolution
    (srcset / lazy-load aware; CDN size params stripped),
  * deduplicates photos by content hash,
  * screenshots the expanded DETAILS accordion (element screenshot),
  * writes info.txt (name, price, URL) per product,
  * prints a summary table at the end.

Output layout (one folder per product, in category display order):
    <out>/1/photo_1.jpg, photo_2.jpg, ..., details.png, info.txt
    <out>/2/...
    ...

Defaults:
  * Windows: output to D:\\jewels\\neckless\\1 and runs HEADED (visible browser).
  * Linux/macOS: output to ./jewels/neckless/1 and runs headless.

Usage:
    pip install playwright requests pillow
    playwright install chromium
    python catalog_scraper.py                     # scrape default category
    python catalog_scraper.py --category-url https://example.com/collections/rings
    python catalog_scraper.py --out "D:/jewels/rings/1" --limit 10
    python catalog_scraper.py --products-file products.txt   # skip discovery

If the URL is a single product page rather than a listing, it is scraped as
product 1. Detection ladder per page: site-tuned rules first, then generic
structural heuristics (price cards for tiles; thumbnail clusters plus the
largest image for galleries; JSON-LD for name/price).

Be polite: keeps a 2-3 s delay between page loads, one retry per failure,
and continues with the remaining products if one fails.
"""

import argparse
import hashlib
import io
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs

import requests

try:
    from PIL import Image
except ImportError:
    Image = None

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DEFAULT_CATEGORY = "https://www.quince.com/women/jewelry/necklaces-all/lab-grown-diamond-necklaces"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
EXCLUDE_IMAGE_HOSTS = ["review-images.onequince.com"]  # customer review photos
DEFAULT_DETAILS_LABELS = ["details", "product details", "description",
                          "specifications", "product information"]
NON_PRODUCT_PATHS = re.compile(
    r"/(cart|checkout|log-?in|sign-?in|register|account|wishlist|search|faq|"
    r"about|privacy|terms|contact|refer|gift-card|blog|help)", re.I)
NAV_TIMEOUT_MS = 60_000

# ---------------------------------------------------------------- JS snippets

JS_COLLECT_ANCHORS = """
() => {
  const out = [];
  document.querySelectorAll('a[href]').forEach((a) => {
    let href;
    try { href = new URL(a.getAttribute('href'), location.href); } catch (e) { return; }
    if (href.origin !== location.origin) return;
    const inHeading = !!(a.closest('h1,h2,h3,h4') || a.querySelector('h1,h2,h3,h4'));
    const hasImg = !!a.querySelector('img');
    let card = a, cardHasPrice = false;
    for (let hops = 0; card && hops < 5; hops++) {
      const t = card.textContent || '';
      if (t.length < 900 && /\\$\\s?\\d/.test(t)) { cardHasPrice = true; break; }
      card = card.parentElement;
    }
    out.push({
      href: href.href, path: href.pathname, search: href.search,
      text: (a.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 160),
      inHeading, hasImg, cardHasPrice,
    });
  });
  return { pageUrl: location.href, items: out, bodyText: document.body.innerText.slice(0, 4000) };
}
"""

JS_COLLECT_IMAGES = """
() => {
  const items = [];
  document.querySelectorAll('img').forEach((img, idx) => {
    const srcs = [];
    const push = (v) => { if (v && typeof v === 'string') srcs.push(v.trim()); };
    push(img.currentSrc);
    push(img.getAttribute('src'));
    push(img.getAttribute('data-src'));
    let best = null, bestW = -1;
    const ss = [img.getAttribute('srcset'), img.getAttribute('data-srcset')]
      .filter(Boolean).join(', ');
    ss.split(',').map(s => s.trim()).filter(Boolean).forEach(entry => {
      const parts = entry.split(/\\s+/);
      const d = parts[1] || '';
      let w = 0;
      if (d.endsWith('w')) w = parseInt(d, 10) || 0;
      else if (d.endsWith('x')) w = (parseFloat(d) || 0) * 1000;
      if (w >= bestW) { bestW = w; best = parts[0]; }
    });
    push(best);
    const pic = img.closest('picture');
    if (pic) pic.querySelectorAll('source').forEach(s => {
      (s.getAttribute('srcset') || '').split(',').forEach(e => push(e.trim().split(/\\s+/)[0]));
    });
    const r = img.getBoundingClientRect();
    items.push({
      idx,
      srcs: srcs.filter(Boolean),
      renderW: r.width,
      renderH: r.height,
      inAnchor: !!img.closest('a'),
      inChrome: !!img.closest('header, footer, nav, [role="dialog"]'),
      alt: img.getAttribute('alt') || '',
    });
  });
  return items;
}
"""

JS_FIND_DETAILS = """
(labels) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const h1 = document.querySelector('h1');
  const nodes = document.querySelectorAll(
    'button, summary, [role="button"], h2, h3, h4, div, span, p');
  let headerEl = null;
  for (const want of labels) {
    for (const el of nodes) {
      let own = '';
      for (const n of el.childNodes) if (n.nodeType === Node.TEXT_NODE) own += n.textContent;
      let txt = norm(own);
      if (!txt && el.children.length === 0) txt = norm(el.textContent);
      if (txt !== want) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 2 && r.height < 2) continue;
      if (h1 && !(h1.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
      headerEl = el;
      break;
    }
    if (headerEl) break;
  }
  if (!headerEl) return null;
  const clickable = headerEl.closest('button, summary, [role="button"], [aria-expanded]') || headerEl;
  return { clickable };
}
"""

# Locate the content panel a DETAILS header controls and report its rendered
# height, so the caller can tell an open panel from a closed one by measuring
# it before and after clicking. The panel is the aria-controls target, else
# the nearest following sibling that has real text and is NOT itself another
# accordion toggle (this is what stops it locking onto the next section's
# header, e.g. MATERIALS below DETAILS). Also returns the box of the tightest
# element wrapping both header and panel, for the screenshot.
JS_DETAILS_STATE = """
(o) => {
  const h = o.clickable;
  const doc = h.ownerDocument;
  const isToggle = (el) =>
    el.matches('button, summary, [role="button"], [aria-expanded]') ||
    !!el.querySelector('button, summary, [role="button"], [aria-expanded]');
  let panel = null;
  const ac = h.getAttribute('aria-controls');
  if (ac) panel = doc.getElementById(ac);
  if (!panel) {
    let base = h;
    for (let hops = 0; base && hops < 3 && !panel; hops++) {
      let sib = base.nextElementSibling;
      while (sib) {
        const r = sib.getBoundingClientRect();
        if (r.height > 6 && (sib.innerText || '').trim().length > 15 && !isToggle(sib)) {
          panel = sib; break;
        }
        sib = sib.nextElementSibling;
      }
      base = base.parentElement;
    }
  }
  const hr = h.getBoundingClientRect();
  const panelH = panel ? panel.getBoundingClientRect().height : 0;
  let container = h;
  if (panel && panelH > 6) {
    let c = h;
    while (c && !(c.contains(panel) && c.contains(h))) c = c.parentElement;
    if (c && c.getBoundingClientRect().height <= panelH + hr.height + 120) container = c;
    else container = panel;   // wrapper too big: screenshot just the content panel
  }
  return { panelH, ariaExpanded: h.getAttribute('aria-expanded'), container, panel };
}
"""

# Extract the DETAILS panel's text as clean, notepad-ready lines. Uses
# textContent (not a screenshot), so it works even when the window is
# minimised or the panel never visually painted - list items become bullet
# lines, paragraphs stay on their own lines, blank runs collapse.
JS_PANEL_TEXT = """
(panel) => {
  if (!panel) return '';
  const norm = s => (s || '').replace(/\\u00a0/g, ' ').replace(/[ \\t]+/g, ' ').trim();
  const lines = [];
  const push = (t, bullet) => { t = norm(t); if (t) lines.push(bullet ? '- ' + t : t); };
  const lis = panel.querySelectorAll('li');
  if (lis.length) {
    panel.querySelectorAll('p, li').forEach(
      el => push(el.textContent, el.tagName.toLowerCase() === 'li'));
  } else {
    const raw = panel.innerText || panel.textContent || '';
    raw.split('\\n').forEach(l => push(l, false));
  }
  const out = [];
  for (const l of lines) if (l !== out[out.length - 1]) out.push(l);
  return out.join('\\n');
}
"""

# Injected before any page script runs: hides the most common automation
# tells (navigator.webdriver, missing chrome object, empty plugins) so sites
# with lighter bot-detection treat the browser as an ordinary Chrome.
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || { runtime: {} };
try {
  const q = window.navigator.permissions && window.navigator.permissions.query;
  if (q) window.navigator.permissions.query = (p) =>
    (p && p.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : q(p));
} catch (e) {}
"""

# Text/status that means an anti-bot interstitial is showing rather than the
# real page (Cloudflare, PerimeterX/HUMAN, Akamai, Imperva, generic WAFs).
CHALLENGE_MARKERS = re.compile(
    r"(just a moment|pardon our interruption|access denied|attention required|"
    r"verify you are (a )?human|checking your browser|enable javascript and cookies|"
    r"cf-browser-verification|px-captcha|please verify you are|unusual traffic|"
    r"request unsuccessful|bot detection|are you a robot)", re.I)


class SiteBlocked(Exception):
    """Raised when a site's anti-bot protection prevents reading any products."""


# ------------------------------------------------------------------- helpers


def log(msg):
    print(msg, flush=True)


def polite_sleep(args):
    time.sleep(random.uniform(args.min_delay, args.max_delay))


def strip_image_params(url):
    """Undo CDN/theme resizing to reach the original file: drop the query
    string (imgix/Contentful-style w=/h=/q= params) and size-suffixed
    filenames (Shopify photo_600x.jpg, WordPress photo-300x300.jpg, @2x).
    Downloads fall back to the original URL if the stripped one fails."""
    parts = urlsplit(url)
    path = re.sub(r"(_\d{2,4}x\d{0,4}|-\d{2,4}x\d{2,4}|@2x)(?=\.\w+$)", "", parts.path)
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def canonical_product_key(url):
    """Product identity = path + color variant (other params are tracking noise)."""
    parts = urlsplit(url)
    color = parse_qs(parts.query).get("color", [""])[0]
    return f"{parts.path}?color={color}"


def clean_product_url(url):
    parts = urlsplit(url)
    color = parse_qs(parts.query).get("color", [""])[0]
    query = f"color={color}" if color else ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def host_matches(netloc, patterns):
    return any(p in netloc for p in patterns)


def sanitize_folder_name(name, max_len=70):
    """Turn a product name into a safe folder name for Windows/macOS/Linux:
    drop characters no filesystem allows, collapse whitespace, trim length,
    and never end in a space or dot (Windows rejects those)."""
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", name or "")
    name = re.sub(r"\s+", " ", name).strip().strip(".").strip()
    return name[:max_len].rstrip(" .")


def dismiss_overlays(page):
    """Close cookie banners / newsletter modals if they appear."""
    selectors = [
        "#onetrust-accept-btn-handler",
        "button:has-text('Accept All')",
        "button:has-text('Accept all')",
        "[role='dialog'] [aria-label*='close' i]",
        "[role='dialog'] button:has-text('No, thanks')",
        "[aria-label*='close' i]",
        "[data-testid*='close' i]",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=400):
                loc.click(timeout=1500)
                page.wait_for_timeout(400)
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def _page_text(page):
    try:
        title = page.title() or ""
    except Exception:
        title = ""
    try:
        body = page.evaluate(
            "() => document.body ? document.body.innerText.slice(0, 3000) : ''")
    except Exception:
        body = ""
    return title, body


def goto_resilient(page, url, what="page"):
    """Navigate to url, tolerating bot-protection interstitials. Returns
    (http_status, challenged). Waits out and reloads through challenge pages
    a few times; a page that clears is treated as success. Never raises for
    a challenge - callers decide what to do when `challenged` is True."""
    status = None
    try:
        resp = page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
        status = resp.status if resp else None
    except PWTimeout:
        pass
    page.wait_for_timeout(2500)
    for attempt in range(1, 4):
        title, body = _page_text(page)
        challenged = bool(CHALLENGE_MARKERS.search(f"{title} {body}")) or status in (403, 429, 503)
        if not challenged:
            return status, False
        log(f"    {what}: anti-bot check detected (HTTP {status}); "
            f"waiting for it to clear ({attempt}/3)...")
        page.wait_for_timeout(5000 + attempt * 3000)
        title, body = _page_text(page)
        if not CHALLENGE_MARKERS.search(f"{title} {body}") and status not in (403, 429, 503):
            log(f"    {what}: cleared.")
            return status, False
        if attempt < 3:
            try:
                resp = page.reload(timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
                status = resp.status if resp else status
                page.wait_for_timeout(2500)
            except PWTimeout:
                pass
    title, body = _page_text(page)
    still = bool(CHALLENGE_MARKERS.search(f"{title} {body}")) or status in (403, 429, 503)
    return status, still


BLOCK_HELP = (
    "This site is protected by anti-bot software and blocked the automated "
    "browser (HTTP 403 / challenge page), so no products could be read.\n"
    "  * Large retailers and marketplaces (Brilliant Earth, Amazon, Etsy, ...) "
    "actively block scrapers - often nothing can get through.\n"
    "  * Make sure 'Show the browser while it works' is ticked - a visible "
    "browser passes more checks than a hidden one.\n"
    "  * Try again in a minute, or solve any 'verify you are human' box by hand "
    "in the browser window the moment it appears.\n"
    "  * Smaller brand shops (especially Shopify stores) usually work fine.")


def new_http_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/jpeg,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca:
        s.verify = ca
    return s


# -------------------------------------------------------- category discovery


def discover_products(page, args, out_root):
    shop = shopify_collection_products(page.context, args.category_url, args.limit)
    if shop:
        log(f"Shopify collection detected - {len(shop)} products via products.json")
        return shop
    log(f"Opening category page: {args.category_url}")
    status, challenged = goto_resilient(page, args.category_url, "category page")
    if challenged:
        log("  the site is showing an anti-bot page; still trying to read products...")
    dismiss_overlays(page)

    try:
        page.wait_for_selector("a[href*='color=']", timeout=6_000)
    except PWTimeout:
        try:
            page.wait_for_selector("a[href] img", timeout=10_000)
        except PWTimeout:
            log("  warning: no product-looking links appeared, continuing anyway")

    cat_path = urlsplit(args.category_url).path.rstrip("/")
    seen, ordered = set(), []            # strict (Quince-style) tile links
    gen_seen, gen_ordered = set(), []    # generic price-card tile links

    def harvest():
        data = page.evaluate(JS_COLLECT_ANCHORS)
        for it in data["items"]:
            if "tracker=" in it["search"]:
                continue                      # recommendation carousels
            if it["path"].rstrip("/") == cat_path:
                continue                      # subcollection tiles / self links
            if NON_PRODUCT_PATHS.search(it["path"]) or not it["path"].strip("/"):
                continue
            candidate_card = (it["inHeading"] or it["hasImg"]) and it["cardHasPrice"]
            if not candidate_card:
                continue
            key = canonical_product_key(it["href"])
            entry = {"url": clean_product_url(it["href"]), "tile_text": it["text"]}
            if "color=" in it["search"] and not args.loose_discovery:
                if key not in seen:
                    seen.add(key)
                    ordered.append(entry)
            if key not in gen_seen:
                gen_seen.add(key)
                gen_ordered.append(entry)
        return data

    # Scroll to the bottom in steps to trigger lazy loading, harvesting as we go.
    stable_rounds = 0
    for _ in range(14):
        data = harvest()
        count_before = len(ordered)
        page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight * 1.6))")
        page.wait_for_timeout(800)
        harvest()
        if len(ordered) >= args.limit and len(ordered) == count_before:
            stable_rounds += 1
            if stable_rounds >= 2:
                break
        else:
            stable_rounds = 0
        at_bottom = page.evaluate(
            "() => (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 4")
        if at_bottom and len(ordered) >= args.limit:
            break
    dismiss_overlays(page)
    data = harvest()

    m = re.search(r"(\d+)\s+items", data.get("bodyText", ""), re.I)
    if m:
        log(f"  category reports {m.group(1)} items")

    if len(ordered) < args.limit and gen_ordered:
        known = {canonical_product_key(p["url"]) for p in ordered}
        extra = [p for p in gen_ordered if canonical_product_key(p["url"]) not in known]
        if extra:
            log(f"  strict tile rule found {len(ordered)}; adding "
                f"{len(extra)} generic price-card links")
            ordered.extend(extra)

    debug_path = out_root / "_category_debug.json"
    debug_path.write_text(json.dumps({"discovered": ordered, "all_anchors": data["items"]},
                                     indent=2), encoding="utf-8")
    if not ordered and challenged:
        raise SiteBlocked(BLOCK_HELP)
    if len(ordered) < args.limit:
        log(f"  warning: only {len(ordered)} product links found "
            f"(wanted {args.limit}); anchor dump: {debug_path}")
    return ordered[: args.limit]


# ------------------------------------------------------------- product pages


def extract_name_price(page):
    name, price = "", ""
    for block in page.locator("script[type='application/ld+json']").all():
        try:
            data = json.loads(block.text_content() or "")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        for node in stack:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)
            if str(node.get("@type", "")).lower() != "product":
                continue
            name = name or str(node.get("name", "")).strip()
            offers = node.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            raw = offers.get("price") or offers.get("lowPrice")
            if raw not in (None, ""):
                try:
                    price = f"${float(raw):,.2f}"
                except (TypeError, ValueError):
                    price = str(raw)
    if not name:
        try:
            name = page.locator("h1").first.inner_text(timeout=5000).strip()
        except Exception:
            name = ""
    if not price:
        try:
            body = page.inner_text("body", timeout=5000)
            h1_pos = body.find(name) if name else -1
            tail = body[h1_pos:] if h1_pos >= 0 else body
            m = re.search(r"(From\s*[\r\n ]*)?([$€£₹]\s?[\d][\d,.]*)", tail)
            if m:
                price = ("From " if m.group(1) else "") + m.group(2).strip()
        except Exception:
            pass
    return name, price


def context_get_json(context, url):
    """GET url through the browser context (carries the site's cookies/session)
    and parse JSON. Returns None on any failure or non-JSON response."""
    try:
        resp = context.request.get(url, timeout=25000)
        if resp.ok and "json" in resp.headers.get("content-type", "").lower():
            return resp.json()
    except Exception:
        pass
    return None


def shopify_product(context, url):
    """If url is a Shopify product page, fetch its full data via <url>.json.
    Returns {name, price, images:[full-res urls]} or None. This bypasses the
    rendered DOM entirely - reliable on the whole Shopify ecosystem."""
    base = url.split("?")[0].rstrip("/")
    if "/products/" not in base:
        return None
    data = context_get_json(context, base + ".json")
    prod = (data or {}).get("product")
    if not isinstance(prod, dict):
        return None
    # Prefer the main gallery (images not tied to a specific variant) so a
    # personalised product - e.g. an A-Z alphabet necklace with a photo per
    # letter - doesn't explode into hundreds of near-duplicate variant shots.
    imgs = prod.get("images", [])
    main = [im["src"] for im in imgs if im.get("src") and not im.get("variant_ids")]
    images = main if main else [im["src"] for im in imgs if im.get("src")]
    price = ""
    variants = prod.get("variants") or []
    if variants and variants[0].get("price") not in (None, ""):
        try:
            price = f"${float(variants[0]['price']):,.2f}"
        except (TypeError, ValueError):
            price = str(variants[0]["price"])
    return {"name": prod.get("title", ""), "price": price, "images": images}


def shopify_collection_products(context, category_url, limit):
    """If category_url is a Shopify collection, list its products via
    products.json. Returns [{url, tile_text}, ...] or []."""
    parts = urlsplit(category_url)
    if "/collections/" not in parts.path:
        return []
    base = f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"
    out, page_no = [], 1
    while len(out) < limit and page_no <= 6:
        data = context_get_json(context, f"{base}/products.json?limit=250&page={page_no}")
        prods = (data or {}).get("products") or []
        if not prods:
            break
        for p in prods:
            if p.get("handle"):
                out.append({"url": f"{parts.scheme}://{parts.netloc}/products/{p['handle']}",
                            "tile_text": p.get("title", "")})
        page_no += 1
    return out[:limit]


def gallery_from_metadata(page):
    """Product images declared in the page's structured data: JSON-LD
    Product.image[] and og:image. These are canonical, full-resolution, and
    present on most e-commerce sites even when the DOM gallery is awkward."""
    urls = []
    for block in page.locator("script[type='application/ld+json']").all():
        try:
            data = json.loads(block.text_content() or "")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        for node in stack:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)
            if str(node.get("@type", "")).lower() != "product":
                continue
            img = node.get("image")
            candidates = img if isinstance(img, list) else [img]
            for c in candidates:
                if isinstance(c, str):
                    urls.append(c)
                elif isinstance(c, dict) and c.get("url"):
                    urls.append(c["url"])
    try:
        for m in page.locator(
                "meta[property='og:image'], meta[property='og:image:secure_url'], "
                "meta[name='og:image']").all():
            c = m.get_attribute("content")
            if c:
                urls.append(c)
    except Exception:
        pass
    out = {}
    for u in urls:
        u = (u or "").strip()
        if u.startswith("//"):
            u = "https:" + u
        if u.startswith("http") and ".svg" not in u.lower():
            out.setdefault(strip_image_params(u), u)
    return list(out.items())


def collect_gallery_urls(page, args):
    """Return ordered, deduped [(bare_url, original_url), ...] for the gallery.

    Strict pass first: on Quince PDPs the gallery is exactly the thumbnail
    rail (small imgs loaded with w=200-499 resize params) plus the main
    viewer (first large img loaded at w=1000-1999). Cross-sell carousels
    load at w=662 and are not part of the gallery even when their tiles
    aren't wrapped in <a> tags. Falls back to a broad any-content-image
    scan if the strict pass finds fewer than 2 images.
    """
    items = page.evaluate(JS_COLLECT_IMAGES)
    page_url = page.url

    def absolutize(src):
        absu = urljoin(page_url, src)
        parts = urlsplit(absu)
        if parts.scheme not in ("http", "https"):
            return None, None
        if host_matches(parts.netloc, EXCLUDE_IMAGE_HOSTS):
            return None, None
        if args.image_hosts and not host_matches(parts.netloc, args.image_hosts):
            return None, None
        path = parts.path.lower()
        if ".svg" in path:
            return None, None
        # Accept URLs that end in an image extension, declare an image format
        # in the query, or come from an obvious image/CDN host - many modern
        # CDNs serve images without a file extension. The download step
        # validates Content-Type and size, so being permissive here is safe.
        looks_image = (
            re.search(r"\.(jpe?g|png|webp|avif)(?:$|[?&])", path)
            or re.search(r"(?:format|fm|type)=(?:jpe?g|jpg|png|webp|avif)", parts.query.lower())
            or "/image" in path or "/media" in path or "/cdn/" in path
            or parts.netloc.split(".")[0] in ("images", "cdn", "img", "media", "assets"))
        if not looks_image:
            return None, None
        return absu, strip_image_params(absu)

    usable = []
    for it in items:
        if it["inAnchor"] or it["inChrome"]:
            continue
        pairs = []
        for src in it["srcs"]:
            absu, bare = absolutize(src)
            if bare:
                pairs.append((absu, bare))
        if pairs:
            usable.append({"renderW": it["renderW"], "renderH": it.get("renderH", 0),
                           "pairs": pairs})

    thumb_sig = re.compile(r"[?&]w=[234]\d\d(?!\d)")
    main_sig = re.compile(r"[?&]w=1\d{3}(?!\d)")
    ordered = {}
    main_done = False
    for u in usable:
        is_thumb = (20 <= u["renderW"] < 180
                    and any(thumb_sig.search(a) for a, _ in u["pairs"]))
        is_main = (not main_done and u["renderW"] >= 300
                   and any(main_sig.search(a) for a, _ in u["pairs"]))
        if not (is_thumb or is_main):
            continue
        if is_main:
            main_done = True
        absu, bare = u["pairs"][0]
        ordered.setdefault(bare, absu)
    if len(ordered) >= 2:
        return list(ordered.items())

    # Structural pass (site-agnostic): the gallery = the largest run of
    # small same-area images close together in the DOM (the thumbnail rail)
    # plus the largest rendered image on the page (the main viewer).
    smalls = [(i, u) for i, u in enumerate(usable) if 20 <= u["renderW"] <= 200]
    best_run, run = [], []
    for i, u in smalls:
        if run and i - run[-1][0] > 8:
            if len(run) > len(best_run):
                best_run = run
            run = []
        run.append((i, u))
    if len(run) > len(best_run):
        best_run = run
    structural = {}
    main_img = max(usable, key=lambda u: u["renderW"] * u["renderH"], default=None)
    if main_img and main_img["renderW"] >= 300:
        absu, bare = main_img["pairs"][0]
        structural[bare] = absu
    if len(best_run) >= 3:
        for _, u in best_run:
            absu, bare = u["pairs"][0]
            structural.setdefault(bare, absu)
    if len(structural) >= 2:
        log("    gallery via structural detection (thumbnail cluster + main image)")
        return list(structural.items())

    ordered = {}
    for u in usable:
        if 0 < u["renderW"] < 30:
            continue
        for absu, bare in u["pairs"]:
            ordered.setdefault(bare, absu)
    # Always fold in images the page declares in its structured data - these
    # rescue sites whose DOM gallery is lazy-loaded or oddly structured.
    for bare, absu in gallery_from_metadata(page):
        ordered.setdefault(bare, absu)
    if not ordered:
        # Last resort: any image URL embedded in page JSON (Next.js/Nuxt data).
        html = page.content()
        for m in re.finditer(r"https?://[^\s\"'\\]+\.(?:jpe?g|png|webp)[^\s\"'\\]*", html):
            u = m.group(0)
            parts = urlsplit(u)
            if host_matches(parts.netloc, EXCLUDE_IMAGE_HOSTS):
                continue
            if args.image_hosts and not host_matches(parts.netloc, args.image_hosts):
                continue
            ordered.setdefault(strip_image_params(u), u)
    return list(ordered.items())


def fetch_image_bytes(context, session, url, referer):
    """Download one image, browser-context first (carries the site's cookies
    and referer, so hotlink/anti-bot protection that blocks a plain request
    is bypassed), then a plain-requests fallback."""
    def is_image(head, ctype):
        return ("image" in (ctype or "").lower()
                or head[:3] in (b"\xff\xd8\xff", b"\x89PN") or head[:4] == b"RIFF"
                or head[:4] == b"GIF8")
    try:
        resp = context.request.get(url, headers={"Referer": referer}, timeout=45000)
        if resp.ok:
            body = resp.body()
            if body and is_image(body, resp.headers.get("content-type", "")):
                return body
    except Exception:
        pass
    try:
        r = session.get(url, timeout=60, headers={"Referer": referer})
        if r.ok and r.content and is_image(r.content, r.headers.get("Content-Type", "")):
            return r.content
    except requests.RequestException:
        pass
    return None


def download_photos(context, session, gallery, folder, referer, args):
    saved, hashes, manifest = 0, set(), []
    tried, too_small = 0, 0
    if len(gallery) > args.max_photos:
        log(f"    capping {len(gallery)} candidate images at --max-photos={args.max_photos}")
        gallery = gallery[: args.max_photos]
    for bare, original in gallery:
        candidates = [bare]
        if original != bare:
            candidates.append(original)
        tried += 1
        content, used_url = None, None
        for cand in candidates:
            content = fetch_image_bytes(context, session, cand, referer)
            if content:
                used_url = cand
                break
        if not content:
            continue
        digest = hashlib.sha256(content).hexdigest()
        if digest in hashes:
            continue
        fmt, size = None, (0, 0)
        if Image is not None:
            try:
                with Image.open(io.BytesIO(content)) as im:
                    fmt, size = im.format, im.size
            except Exception:
                continue
            if min(size) < args.min_photo_side:
                too_small += 1
                continue          # icon / swatch, not a product photo
        hashes.add(digest)
        saved += 1
        dest = folder / f"photo_{saved}.jpg"
        if fmt in (None, "JPEG"):
            dest.write_bytes(content)
        else:
            with Image.open(io.BytesIO(content)) as im:
                if im.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", im.size, (255, 255, 255))
                    background.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
                    im = background
                else:
                    im = im.convert("RGB")
                im.save(dest, "JPEG", quality=92)
        manifest.append(f"photo_{saved}.jpg\t{size[0]}x{size[1]}\t{used_url}")
        log(f"    photo_{saved}.jpg  ({size[0]}x{size[1]}, {len(content) // 1024} KB)")
        time.sleep(random.uniform(0.3, 0.7))
    if manifest:
        (folder / "photo_urls.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    if saved == 0 and tried:
        reason = (f"{too_small} were below the {args.min_photo_side}px minimum "
                  f"(try --min-photo-side)" if too_small else
                  "the image host blocked the downloads")
        log(f"    note: found {tried} image URL(s) but saved 0 - {reason}")
    return saved


def capture_details(page, folder, labels):
    handle = page.evaluate_handle(JS_FIND_DETAILS, labels)
    try:
        if not handle or handle.evaluate("v => v === null"):
            log(f"    no section matching {labels} found on page")
            return False
        clickable = handle.get_property("clickable").as_element()
        if clickable is None:
            return False
        clickable.scroll_into_view_if_needed(timeout=8000)
        page.wait_for_timeout(300)

        def measure():
            sh = page.evaluate_handle(JS_DETAILS_STATE, handle)
            return (sh.get_property("panelH").json_value(),
                    str(sh.get_property("ariaExpanded").json_value()).lower(),
                    sh.get_property("container").as_element(),
                    sh.get_property("panel").as_element())

        base_h, aria, container, panel = measure()
        # Already-open panel (a plain description block, or aria says expanded).
        expanded = base_h > 40 or (aria == "true" and base_h > 6)
        clicks = 0
        while not expanded and clicks < 3:
            try:
                clickable.click(timeout=8000)
            except Exception:
                break
            clicks += 1
            page.wait_for_timeout(700)
            base_h2, aria, container, panel = measure()
            # Opened only if the controlled panel actually grew, or aria flipped
            # true with a panel present - not merely that some sibling has size.
            if base_h2 > base_h + 40 or (aria == "true" and base_h2 > 40):
                expanded = True
                break

        # 1) details.txt - the reliable deliverable. Reads the section's text
        #    straight from the DOM, so it is correct even if the browser window
        #    is minimised (which blanks screenshots).
        wrote_txt = False
        target = panel if panel is not None else container
        if target is not None:
            try:
                text = (target.evaluate(JS_PANEL_TEXT) or "").strip()
            except Exception:
                text = ""
            if len(text) >= 3:
                try:
                    label = (clickable.evaluate(
                        "el => (el.textContent || '').replace(/\\s+/g, ' ').trim()")
                        or "").split("\n")[0][:60]
                except Exception:
                    label = ""
                header = (label or "DETAILS").upper()
                (folder / "details.txt").write_text(header + "\n\n" + text + "\n",
                                                    encoding="utf-8")
                wrote_txt = True
                log(f"    details.txt written ({len(text)} chars)")

        # 2) details.png - best effort; may be blank if the window is minimised.
        if expanded and container is not None:
            try:
                page.bring_to_front()
                container.scroll_into_view_if_needed(timeout=5000)
                page.wait_for_timeout(250)
                container.screenshot(path=str(folder / "details.png"))
                log(f"    details.png captured (expanded after {clicks} click(s))")
            except Exception as exc:
                log(f"    details.png skipped ({str(exc).splitlines()[0][:80]})")

        if not wrote_txt:
            log("    DETAILS section found but no text could be extracted")
        return wrote_txt
    except Exception as exc:
        log(f"    DETAILS capture failed: {exc}")
        return False
    finally:
        try:
            handle.dispose()
        except Exception:
            pass


def scrape_product(page, session, product, folder, args):
    url = product["url"]
    status, challenged = goto_resilient(page, url, "product page")
    if status and status >= 400 and not challenged:
        raise RuntimeError(f"HTTP {status}")
    if challenged:
        log("    still behind an anti-bot page; results for this product may be empty")
    dismiss_overlays(page)
    try:
        page.wait_for_selector("h1", timeout=15_000)
    except PWTimeout:
        pass

    # Nudge lazy-loaded gallery thumbs, then return to the top.
    page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight * 0.8))")
    page.wait_for_timeout(600)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)

    context = page.context
    shop = shopify_product(context, url)
    name, price = extract_name_price(page)
    if shop:
        name = shop["name"] or name
        price = shop["price"] or price
    log(f"    name : {name or '(not found)'}")
    log(f"    price: {price or '(not found)'}")

    if shop and shop["images"]:
        gallery, seen = [], set()
        for u in shop["images"]:
            b = strip_image_params(u)
            if b not in seen:
                seen.add(b)
                gallery.append((b, u))
        log(f"    gallery via Shopify product data: {len(gallery)} images")
    else:
        gallery = collect_gallery_urls(page, args)
        log(f"    gallery images found: {len(gallery)}")
    photos = download_photos(context, session, gallery, folder, url, args)

    dismiss_overlays(page)
    details_ok = capture_details(page, folder, args.details_labels)

    (folder / "info.txt").write_text(
        f"Product name: {name}\n"
        f"Price: {price}\n"
        f"URL: {url}\n"
        f"Photos saved: {photos}\n"
        f"Details section: {'saved to details.txt' if details_ok else 'not found'}\n"
        f"Scraped at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
        encoding="utf-8")
    return {"name": name, "price": price, "photos": photos, "details": details_ok}


# ------------------------------------------------------------------ main run


def run(args):
    out_root = Path(args.out).expanduser()
    out_root.mkdir(parents=True, exist_ok=True)
    log(f"Output root: {out_root.resolve()}")

    session = new_http_session()
    results = []

    with sync_playwright() as p:
        # Anti-bot: drop the automation launch flags Chromium normally exposes.
        # Anti-throttle: keep the page rendering when the window is minimised or
        # in the background, otherwise element screenshots (details.png) capture
        # a blank/stale frame because Windows tells Chrome the tab is hidden.
        launch_kwargs = {
            "headless": not args.headed,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
                "--disable-features=CalculateNativeWinOcclusion",
            ],
            "ignore_default_args": ["--enable-automation"],
        }
        if args.chromium_path:
            launch_kwargs["executable_path"] = args.chromium_path
        proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy_url and not args.no_proxy_env:
            launch_kwargs["proxy"] = {"server": proxy_url}
            log(f"Using proxy from environment: {proxy_url}")
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 950},
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
        )
        context.add_init_script(STEALTH_JS)
        page = context.new_page()

        if args.products_file:
            lines = Path(args.products_file).read_text(encoding="utf-8").splitlines()
            products = [{"url": ln.strip(), "tile_text": ""}
                        for ln in lines if ln.strip() and not ln.strip().startswith("#")]
            products = products[: args.limit]
            log(f"Loaded {len(products)} product URLs from {args.products_file}")
        else:
            try:
                products = discover_products(page, args, out_root)
            except SiteBlocked as exc:
                log("\n" + "=" * 64)
                log("COULD NOT SCRAPE THIS SITE")
                log("=" * 64)
                log(str(exc))
                browser.close()
                return 3
            if not products:
                log("No product tiles found; treating the URL as a single product page")
                products = [{"url": args.category_url, "tile_text": ""}]
            log(f"Discovered {len(products)} product URLs (in page order):")
            for i, pr in enumerate(products, 1):
                log(f"  {i:2d}. {pr['url']}")

        for i, product in enumerate(products, 1):
            folder = out_root / str(i)
            folder.mkdir(parents=True, exist_ok=True)
            log(f"\n[{i}/{len(products)}] {product['url']}")
            outcome = None
            for attempt in (1, 2):
                try:
                    outcome = scrape_product(page, session, product, folder, args)
                    break
                except Exception as exc:
                    log(f"    attempt {attempt} failed: {exc}")
                    if attempt == 1:
                        time.sleep(4)
            # Rename "<n>" -> "<n>. <product name>" now that the name is known,
            # so folders are self-describing and still sort in page order.
            disp = ((outcome or {}).get("name") or product.get("tile_text") or "").strip()
            clean = sanitize_folder_name(disp)
            if clean:
                target = out_root / f"{i}. {clean}"
                try:
                    if target != folder and not target.exists():
                        folder.rename(target)
                        folder = target
                        log(f"    folder: {target.name}")
                except OSError:
                    pass
            if outcome is None:
                results.append({"n": i, "name": disp or product["url"], "price": "",
                                "photos": 0, "details": False, "status": "FAILED"})
            else:
                status = "OK" if outcome["photos"] and outcome["details"] else "PARTIAL"
                results.append({"n": i, **outcome, "status": status})
            polite_sleep(args)

        browser.close()

    # ------------------------------------------------------------- summary
    lines = []
    lines.append(f"{'#':>2}  {'Product':<52} {'Price':>12}  {'Photos':>6}  {'Details':>7}  Status")
    lines.append("-" * 100)
    for r in results:
        name = (r["name"][:49] + "...") if len(r["name"]) > 52 else r["name"]
        lines.append(f"{r['n']:>2}  {name:<52} {r.get('price', ''):>12}  "
                     f"{r['photos']:>6}  {('yes' if r['details'] else 'NO'):>7}  {r['status']}")
    failed = [r for r in results if r["status"] == "FAILED"]
    lines.append("-" * 100)
    lines.append(f"Done: {len(results) - len(failed)}/{len(results)} products scraped, "
                 f"{sum(r['photos'] for r in results)} photos total, "
                 f"{sum(1 for r in results if r['details'])} details screenshots.")
    if failed:
        lines.append("Failures: " + ", ".join(f"#{r['n']}" for r in failed))
    table = "\n".join(lines)
    log("\n" + table)
    (out_root / "_summary.txt").write_text(table + "\n", encoding="utf-8")
    return 0 if len(failed) < len(results) else 1


def parse_args(argv=None):
    on_windows = os.name == "nt"
    default_out = r"D:\jewels\neckless\1" if on_windows else "./jewels/neckless/1"
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category-url", default=DEFAULT_CATEGORY)
    ap.add_argument("--out", default=default_out, help=f"output root (default: {default_out})")
    ap.add_argument("--limit", type=int, default=15, help="number of products (default 15)")
    ap.add_argument("--products-file", help="file with product URLs (one per line); "
                                            "skips category discovery")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--headed", dest="headed", action="store_true",
                      help="visible browser window")
    mode.add_argument("--headless", dest="headed", action="store_false")
    ap.set_defaults(headed=on_windows)   # first run on Windows: watch it work
    ap.add_argument("--min-delay", type=float, default=2.0)
    ap.add_argument("--max-delay", type=float, default=3.0)
    ap.add_argument("--image-host", dest="image_hosts", action="append",
                    help="restrict gallery images to hosts containing this "
                         "substring (repeatable; default: auto-detect)")
    ap.add_argument("--details-label", dest="details_labels", action="append",
                    help="section header text to screenshot (repeatable; "
                         f"default: {', '.join(DEFAULT_DETAILS_LABELS)})")
    ap.add_argument("--min-photo-side", type=int, default=350,
                    help="skip images smaller than this on either side (default 350)")
    ap.add_argument("--max-photos", type=int, default=30,
                    help="max photos to save per product (default 30; guards "
                         "against variant-image explosions)")
    ap.add_argument("--loose-discovery", action="store_true",
                    help="skip the site-tuned tile rule and use only the "
                         "generic price-card rule")
    ap.add_argument("--no-proxy-env", action="store_true",
                    help="ignore HTTPS_PROXY from the environment")
    ap.add_argument("--chromium-path",
                    help="use a specific Chromium/Chrome executable instead of "
                         "Playwright's downloaded browser")
    args = ap.parse_args(argv)
    if not args.details_labels:
        args.details_labels = list(DEFAULT_DETAILS_LABELS)
    args.details_labels = [s.strip().lower() for s in args.details_labels]
    return args


if __name__ == "__main__":
    try:
        sys.exit(run(parse_args()))
    except SiteBlocked as exc:
        print("\n" + "=" * 64)
        print("COULD NOT SCRAPE THIS SITE")
        print("=" * 64)
        print(str(exc))
        sys.exit(3)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
