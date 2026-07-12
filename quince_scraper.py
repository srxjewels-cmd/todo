#!/usr/bin/env python3
"""Quince product scraper: gallery photos + DETAILS screenshots.

Scrapes the first N products (default 15) from a Quince category page:
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
    python quince_scraper.py                      # scrape default category
    python quince_scraper.py --headless
    python quince_scraper.py --out "D:/jewels/neckless/1" --limit 15
    python quince_scraper.py --products-file products.txt   # skip discovery

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
IMAGE_HOSTS = ["images.quince.com"]          # gallery CDN(s); override with --image-host
EXCLUDE_IMAGE_HOSTS = ["review-images.onequince.com"]  # customer review photos
MIN_PHOTO_SIDE = 350                         # skip icons/swatches smaller than this
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
      inAnchor: !!img.closest('a'),
      inChrome: !!img.closest('header, footer, nav, [role="dialog"]'),
      alt: img.getAttribute('alt') || '',
    });
  });
  return items;
}
"""

JS_FIND_DETAILS = """
() => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const h1 = document.querySelector('h1');
  let headerEl = null;
  const nodes = document.querySelectorAll(
    'button, summary, [role="button"], h2, h3, h4, div, span, p');
  for (const el of nodes) {
    let own = '';
    for (const n of el.childNodes) if (n.nodeType === Node.TEXT_NODE) own += n.textContent;
    let txt = norm(own);
    if (!txt && el.children.length === 0) txt = norm(el.textContent);
    if (txt !== 'details' && txt !== 'product details') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 && r.height < 2) continue;
    if (h1 && !(h1.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
    headerEl = el;
    break;
  }
  if (!headerEl) return null;
  const clickable = headerEl.closest('button, summary, [role="button"], [aria-expanded]') || headerEl;
  return { clickable };
}
"""

# Assess accordion state relative to the clickable header: locate the content
# panel (aria-controls target, else the nearest following sibling with real
# height, walking up through wrapper levels), report whether it is visibly
# expanded, and expose the tightest element containing both header and panel.
JS_DETAILS_STATE = """
(o) => {
  const h = o.clickable;
  const doc = h.ownerDocument;
  const hr = h.getBoundingClientRect();
  let panel = null;
  const ac = h.getAttribute('aria-controls');
  if (ac) panel = doc.getElementById(ac);
  if (!panel || panel.getBoundingClientRect().height <= 24) {
    let base = h;
    for (let hops = 0; base && hops < 3 && (!panel || panel.getBoundingClientRect().height <= 24); hops++) {
      let sib = base.nextElementSibling;
      while (sib) {
        const r = sib.getBoundingClientRect();
        if (r.height > 24 && (sib.innerText || '').trim().length > 20) { panel = sib; break; }
        sib = sib.nextElementSibling;
      }
      base = base.parentElement;
    }
  }
  const pr = panel ? panel.getBoundingClientRect() : null;
  const expanded = !!pr && pr.height > 24;
  let container = null, rect = null;
  if (expanded) {
    container = h;
    while (container && !(container.contains(panel) && container.contains(h))) {
      container = container.parentElement;
    }
    const top = Math.min(hr.top, pr.top), left = Math.min(hr.left, pr.left);
    const right = Math.max(hr.right, pr.right), bottom = Math.max(hr.bottom, pr.bottom);
    rect = { x: left, y: top + window.scrollY, width: right - left, height: bottom - top };
  }
  return { expanded, container: container || h, rect,
           ariaExpanded: h.getAttribute('aria-expanded') };
}
"""

# ------------------------------------------------------------------- helpers


def log(msg):
    print(msg, flush=True)


def polite_sleep(args):
    time.sleep(random.uniform(args.min_delay, args.max_delay))


def strip_image_params(url):
    """Drop the query string (w/h/q CDN resize params) to get the original file."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


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
    log(f"Opening category page: {args.category_url}")
    resp = page.goto(args.category_url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
    if resp and resp.status >= 400:
        raise RuntimeError(f"category page returned HTTP {resp.status}")
    page.wait_for_timeout(2500)
    dismiss_overlays(page)

    try:
        page.wait_for_selector("a[href*='color=']", timeout=20_000)
    except PWTimeout:
        log("  warning: no product-looking links appeared after 20s, continuing anyway")

    cat_path = urlsplit(args.category_url).path.rstrip("/")
    seen, ordered = set(), []

    def harvest():
        data = page.evaluate(JS_COLLECT_ANCHORS)
        for it in data["items"]:
            if "tracker=" in it["search"]:
                continue                      # recommendation carousels
            if it["path"].rstrip("/") == cat_path:
                continue                      # subcollection tiles / self links
            is_product = ("color=" in it["search"] and (it["inHeading"] or it["hasImg"])
                          and it["cardHasPrice"])
            if not is_product and not (it["inHeading"] and it["cardHasPrice"] and args.loose_discovery):
                continue
            key = canonical_product_key(it["href"])
            if key in seen:
                continue
            seen.add(key)
            ordered.append({"url": clean_product_url(it["href"]), "tile_text": it["text"]})
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

    debug_path = out_root / "_category_debug.json"
    debug_path.write_text(json.dumps({"discovered": ordered, "all_anchors": data["items"]},
                                     indent=2), encoding="utf-8")
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
            m = re.search(r"(From\s*[\r\n ]*)?\$\s?([\d,]+(?:\.\d{2})?)", tail)
            if m:
                price = ("From " if m.group(1) else "") + "$" + m.group(2)
        except Exception:
            pass
    return name, price


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
        if not host_matches(parts.netloc, args.image_hosts):
            return None, None
        path = parts.path.lower()
        if ".svg" in path or not re.search(r"\.(jpe?g|png|webp|avif)$", path):
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
            usable.append({"renderW": it["renderW"], "pairs": pairs})

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
    if ordered:
        log("    strict gallery detection found <2 images, using broad scan")

    ordered = {}
    for u in usable:
        if 0 < u["renderW"] < 30:
            continue
        for absu, bare in u["pairs"]:
            ordered.setdefault(bare, absu)
    if not ordered:
        # Fallback: any page-embedded JSON (Next.js data) mentioning the CDN.
        html = page.content()
        for m in re.finditer(r"https?://[^\s\"'\\]+\.(?:jpe?g|png|webp)[^\s\"'\\]*", html):
            u = m.group(0)
            parts = urlsplit(u)
            if host_matches(parts.netloc, args.image_hosts) and \
               not host_matches(parts.netloc, EXCLUDE_IMAGE_HOSTS):
                bare = strip_image_params(u)
                ordered.setdefault(bare, u)
    return list(ordered.items())


def download_photos(session, gallery, folder, referer, args):
    saved, hashes, manifest = 0, set(), []
    for bare, original in gallery:
        candidates = [bare]
        if original != bare:
            candidates.append(original)
        content, used_url = None, None
        for cand in candidates:
            for attempt in (1, 2):
                try:
                    r = session.get(cand, timeout=60, headers={"Referer": referer})
                    ctype = r.headers.get("Content-Type", "")
                    if r.ok and r.content and ("image" in ctype or r.content[:3] in
                                               (b"\xff\xd8\xff", b"RIF", b"\x89PN")):
                        content, used_url = r.content, cand
                        break
                except requests.RequestException as exc:
                    if attempt == 2:
                        log(f"    image failed twice: {cand} ({exc})")
                    else:
                        time.sleep(1.5)
            if content:
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
            if min(size) < MIN_PHOTO_SIDE:
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
    return saved


def capture_details(page, folder):
    handle = page.evaluate_handle(JS_FIND_DETAILS)
    try:
        if not handle or handle.evaluate("v => v === null"):
            log("    DETAILS section not found on page")
            return False
        clickable = handle.get_property("clickable").as_element()
        if clickable is None:
            return False
        clickable.scroll_into_view_if_needed(timeout=8000)
        page.wait_for_timeout(300)

        state = page.evaluate_handle(JS_DETAILS_STATE, handle)
        expanded = state.get_property("expanded").json_value()
        # An accordion may start open, closed, or get closed by a stray first
        # toggle - keep clicking until the panel is measurably visible.
        clicks = 0
        while not expanded and clicks < 3:
            clickable.click(timeout=8000)
            clicks += 1
            page.wait_for_timeout(800)
            state = page.evaluate_handle(JS_DETAILS_STATE, handle)
            expanded = state.get_property("expanded").json_value()

        dest = str(folder / "details.png")
        if expanded:
            container = state.get_property("container").as_element()
            box = container.bounding_box() if container else None
            if container and box and box["height"] <= 4500:
                container.screenshot(path=dest)
            else:
                rect = state.get_property("rect").json_value()
                clip = {"x": max(rect["x"] - 4, 0), "y": max(rect["y"] - 4, 0),
                        "width": rect["width"] + 8, "height": min(rect["height"] + 8, 4500)}
                page.screenshot(path=dest, clip=clip)
            log(f"    details.png captured (expanded after {clicks} click(s))")
            return True
        hb = clickable.bounding_box()
        if hb:
            clip = {"x": max(hb["x"] - 8, 0), "y": max(hb["y"] - 8, 0),
                    "width": hb["width"] + 16, "height": 620}
            page.screenshot(path=str(folder / "details.png"), clip=clip)
        log("    DETAILS panel never became visible; saved best-effort region only")
        return False
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
    resp = page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
    if resp and resp.status >= 400:
        raise RuntimeError(f"HTTP {resp.status}")
    page.wait_for_timeout(2500)
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

    name, price = extract_name_price(page)
    log(f"    name : {name or '(not found)'}")
    log(f"    price: {price or '(not found)'}")

    gallery = collect_gallery_urls(page, args)
    log(f"    gallery images found: {len(gallery)}")
    photos = download_photos(session, gallery, folder, url, args)

    dismiss_overlays(page)
    details_ok = capture_details(page, folder)

    (folder / "info.txt").write_text(
        f"Product name: {name}\n"
        f"Price: {price}\n"
        f"URL: {url}\n"
        f"Photos saved: {photos}\n"
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
        launch_kwargs = {"headless": not args.headed}
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
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = context.new_page()

        if args.products_file:
            lines = Path(args.products_file).read_text(encoding="utf-8").splitlines()
            products = [{"url": ln.strip(), "tile_text": ""}
                        for ln in lines if ln.strip() and not ln.strip().startswith("#")]
            products = products[: args.limit]
            log(f"Loaded {len(products)} product URLs from {args.products_file}")
        else:
            products = discover_products(page, args, out_root)
            log(f"Discovered {len(products)} product URLs (in page order):")
            for i, pr in enumerate(products, 1):
                log(f"  {i:2d}. {pr['url']}")

        # Create the full folder structure up front: <out>/1 ... <out>/N
        for i in range(1, len(products) + 1):
            (out_root / str(i)).mkdir(parents=True, exist_ok=True)

        for i, product in enumerate(products, 1):
            folder = out_root / str(i)
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
            if outcome is None:
                results.append({"n": i, "name": product.get("tile_text") or product["url"],
                                "price": "", "photos": 0, "details": False,
                                "status": "FAILED"})
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
                    help="allowed gallery image host substring "
                         "(repeatable; default images.quince.com)")
    ap.add_argument("--loose-discovery", action="store_true",
                    help="relax product-link detection if the strict rule finds too few")
    ap.add_argument("--no-proxy-env", action="store_true",
                    help="ignore HTTPS_PROXY from the environment")
    ap.add_argument("--chromium-path",
                    help="use a specific Chromium/Chrome executable instead of "
                         "Playwright's downloaded browser")
    args = ap.parse_args(argv)
    if not args.image_hosts:
        args.image_hosts = list(IMAGE_HOSTS)
    return args


if __name__ == "__main__":
    try:
        sys.exit(run(parse_args()))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
