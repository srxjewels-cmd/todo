#!/usr/bin/env python3
r"""Scrape Quince lab-grown-diamond jewelry into a variant catalog.

For each category it finds product pages, reads each product's __NEXT_DATA__
(colours+hex, sizes, per-colour+per-carat price, original price, rating,
per-colour images, details) and groups sibling pages by base design.

  design = one card with Color swatches + Carat + Size options; each
  (colour x carat) variant carries its own price and its own photos, so the
  gallery changes when either the colour OR the carat is changed.

Images are downloaded + resized under docs/photos/<designId>/<n>.jpg and
referenced by relative path. Writes shopdata/variants.json.
"""
import re, io, json, time, html as htmlmod, pathlib
import requests
from PIL import Image

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Referer": "https://www.quince.com/",
                  "Accept": "text/html,application/json,image/*,*/*"})

CATS = {
    "Necklaces": "https://www.quince.com/shop/women/jewelry/necklaces-all/lab-grown-diamond-necklaces",
    "Bracelets": "https://www.quince.com/shop/women/jewelry/bracelets-all?filter=materials%3DLab%2520Grown%2520Diamond",
    "Rings":     "https://www.quince.com/shop/women/jewelry/rings-all?filter=materials%3DLab%2520Grown%2520Diamond",
    "Earrings":  "https://www.quince.com/shop/women/jewelry/earrings-all?filter=materials%3DLab%2520Grown%2520Diamond",
}
ENGAGEMENT_KW = ["engagement", "bridal"]
COLOR_HEX = {"Yellow Gold": "#E6C46A", "White Gold": "#E5E5E8", "Rose Gold": "#E6B7A9",
             "Platinum": "#D8D8DE", "Gold Vermeil": "#E6C46A", "Sterling Silver": "#DCDCE0",
             "Gold": "#E6C46A", "Silver": "#DCDCE0"}
COLORS = list(COLOR_HEX)
# map a metal colour to Quince's simplified Color-filter bucket + Material
QCOLOR = {"yellow gold": "Yellow", "white gold": "White", "rose gold": "Pink",
          "platinum": "Grey", "gold vermeil": "Yellow", "sterling silver": "Grey",
          "gold": "Yellow", "silver": "Grey", "pink gold": "Pink"}
QMETAL = {"yellow gold": "14k Gold", "white gold": "14k Gold", "rose gold": "14k Gold",
          "platinum": "Platinum", "gold vermeil": "Gold Vermeil",
          "sterling silver": "Sterling Silver", "gold": "14k Gold", "silver": "Sterling Silver"}


def get(url):
    for a in (1, 2, 3):
        try:
            r = S.get(url, timeout=45)
            if r.ok:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(1.2 * a)
    return ""


def next_data(h):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    try:
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None


def category_slugs(url, want=400):
    slugs, seen = [], set()
    for page in range(1, 9):
        u = url + (("&" if "?" in url else "?") + f"page={page}") if page > 1 else url
        h = get(u)
        if not h:
            break
        d = next_data(h)
        found = []

        def walk(o):
            if isinstance(o, dict):
                s = o.get("slug")
                if s and (o.get("productDomainTypes") or o.get("spid") or
                          str(o.get("typename", "")).lower() == "product"):
                    found.append(s)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        if d:
            walk(d)
        if not found:
            found = [s for s in re.findall(r'/women/([a-z0-9\-]+)', h) if "diamond" in s]
        new = 0
        for s in found:
            if "diamond" in s and s not in seen:
                seen.add(s)
                slugs.append(s)
                new += 1
        if new == 0:
            break
        if len(slugs) >= want:
            break
    return slugs


def clean_details(s):
    if not s:
        return ""
    s = re.sub(r"</li>", "\n", s)
    s = re.sub(r"<li>", "- ", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmlmod.unescape(s)
    return "\n".join(l.strip() for l in s.splitlines() if l.strip())


CARAT_RE = re.compile(r"([\d.]+)\s*ct(?:tw|w)?", re.I)


def carat_of(title, slug):
    m = CARAT_RE.search(title) or CARAT_RE.search(slug.replace("-", " "))
    if not m:
        return None
    return f"{m.group(1).rstrip('.')}ctw"


def strip_variant_bits(title):
    t = re.sub(r"\s+in\s+(%s)\s*$" % "|".join(map(re.escape, COLORS)), "", title, flags=re.I)
    t = CARAT_RE.sub("", t)
    t = re.sub(r"[-–]\s*$", "", t).strip(" -–")
    return re.sub(r"\s{2,}", " ", t).strip()


def amt(x):
    if isinstance(x, dict):
        return x.get("amount")
    return x


def product_url(slug):
    slug = slug.lstrip("/")
    if slug.startswith(("women/", "men/")):
        return "https://www.quince.com/" + slug
    return "https://www.quince.com/women/" + slug


def scrape_product(slug):
    h = get(product_url(slug))
    d = next_data(h)
    if not d:
        return None
    try:
        p = d["props"]["pageProps"]["pageData"]["context"]["pageDataJson"]["product"]
    except Exception:
        return None
    title = (p.get("title") or "").strip()
    variants = p.get("variants") or []
    colours = []
    for c in (p.get("new_color_options") or []):
        colours.append({"label": c["value"],
                        "hex": (c.get("hexCode") or COLOR_HEX.get(c["value"], "#ccc")).strip()})
    if not colours:
        for v in variants:
            for o in v.get("options", []):
                if o.get("name") == "Color" and o["value"] not in [x["label"] for x in colours]:
                    colours.append({"label": o["value"], "hex": COLOR_HEX.get(o["value"], "#ccc")})
    if not colours:
        colours = [{"label": "", "hex": "#ccc"}]
    sizes = []
    for v in variants:
        for o in v.get("options", []):
            nm, val = o.get("name"), o.get("value")
            if nm and nm != "Color" and val and val != "One Size" and val not in sizes:
                sizes.append(val)
    # price + original price, per colour
    price_by_color, orig_by_color = {}, {}
    overall = None
    for v in variants:
        a = amt(v.get("price"))
        cols = [o["value"] for o in v.get("options", []) if o.get("name") == "Color"]
        key = cols[0] if cols else "_all"
        if a is not None:
            overall = a if overall is None else min(overall, a)
            price_by_color[key] = a if key not in price_by_color else min(price_by_color[key], a)
        ob = amt(v.get("traditionalRetailPrice"))
        if ob:
            orig_by_color[key] = ob if key not in orig_by_color else min(orig_by_color[key], ob)
    # rating / reviews (best effort)
    rating, reviews = None, None
    ps = json.dumps(p)
    m = re.search(r'"(?:averageRating|starRating|ratingValue|averageReviewRating|rating)":\s*([\d.]+)', ps)
    if m:
        try:
            rating = round(float(m.group(1)), 1)
            if rating > 5:
                rating = None
        except Exception:
            pass
    m2 = re.search(r'"(?:reviewCount|ratingCount|numReviews|totalReviews|reviewsCount)":\s*(\d+)', ps)
    if m2:
        reviews = int(m2.group(1))
    # images per colour
    imgs_by_color = {}
    for im in p.get("images", []):
        u = (im.get("image") or {}).get("url", "")
        if not u:
            continue
        if u.startswith("//"):
            u = "https:" + u
        cols = []
        for o in im.get("options", []):
            if o.get("name") == "Color":
                cols = o.get("values", [])
        key = cols[0] if cols else "_all"
        imgs_by_color.setdefault(key, []).append(u)
    return {"title": title, "slug": slug, "colours": colours, "sizes": sizes,
            "price_by_color": price_by_color, "orig_by_color": orig_by_color,
            "overall": overall, "rating": rating, "reviews": reviews,
            "imgs_by_color": imgs_by_color,
            "details": clean_details(p.get("details", "")), "carat": carat_of(title, slug)}


def norm(s):
    return re.sub(r"1[048]k|[^a-z0-9]", "", s.lower())


def download(url, dest_full, dest_thumb):
    try:
        r = S.get(url + ("&" if "?" in url else "?") + "w=1600", timeout=45)
        if not (r.ok and r.content):
            r = S.get(url, timeout=45)
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return False
    w, h = im.size
    if w > 1500:
        im = im.resize((1500, round(h * 1500 / w)))
    im.save(dest_full, "JPEG", quality=85, optimize=True)
    w, h = im.size
    tw = min(600, w)
    im.resize((tw, round(h * tw / w))).save(dest_thumb, "JPEG", quality=78, optimize=True)
    return True


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "x"


def main():
    photos = pathlib.Path("docs/photos")
    photos.mkdir(parents=True, exist_ok=True)
    designs = {}
    dcount = 0
    for cat, url in CATS.items():
        slugs = category_slugs(url)
        print(f"[{cat}] {len(slugs)} product slugs", flush=True)
        for slug in slugs:
            rec = scrape_product(slug)
            if not rec or rec["overall"] is None:
                continue
            base = strip_variant_bits(rec["title"]) or slug
            realcat = cat
            if cat == "Rings":
                hay = (rec["title"] + " " + rec["details"]).lower()
                realcat = "Engagement Rings" if any(k in hay for k in ENGAGEMENT_KW) else "Rings"
            key = (realcat, base)
            d = designs.get(key)
            if not d:
                dcount += 1
                d = designs[key] = {"id": f"D{dcount:03d}", "cat": realcat, "name": base,
                                    "colours": {}, "carats": [], "sizes": [],
                                    "details": "", "rating": None, "reviews": None, "rows": []}
            for c in rec["colours"]:
                if c["label"] and c["label"] not in d["colours"]:
                    d["colours"][c["label"]] = c["hex"]
            if rec["carat"] and rec["carat"] not in d["carats"]:
                d["carats"].append(rec["carat"])
            for s in rec["sizes"]:
                if s not in d["sizes"]:
                    d["sizes"].append(s)
            if rec["details"] and len(rec["details"]) > len(d["details"]):
                d["details"] = rec["details"]
            if rec["rating"] and (d["rating"] is None or (rec["reviews"] or 0) > (d["reviews"] or 0)):
                d["rating"], d["reviews"] = rec["rating"], rec["reviews"]
            d["rows"].append(rec)
        time.sleep(0.3)

    out = []
    for (cat, base), d in designs.items():
        did = d["id"]
        colour_labels = list(d["colours"].keys())
        carats = sorted(d["carats"], key=lambda x: float(re.sub(r"[^\d.]", "", x) or 0))
        multi_carat = len(carats) >= 2

        # per-design image cache: unique URL -> {full,thumb} rel paths (dedupes shared photos)
        imgcache, counter = {}, [0]

        def fetch(urls):
            rels = []
            for u in urls[:6]:
                if u in imgcache:
                    if imgcache[u]:
                        rels.append(imgcache[u])
                    continue
                counter[0] += 1
                n = counter[0]
                full = photos / did / f"{n}.jpg"
                thumb = photos / did / f"{n}_t.jpg"
                full.parent.mkdir(parents=True, exist_ok=True)
                if download(u, full, thumb):
                    imgcache[u] = {"full": f"photos/{did}/{n}.jpg", "thumb": f"photos/{did}/{n}_t.jpg"}
                    rels.append(imgcache[u])
                else:
                    imgcache[u] = None
            return rels

        def imgs_for(rec, colour):
            ic = rec["imgs_by_color"]
            if ic.get(colour):
                urls = ic[colour]
            else:
                cn = norm(colour)
                urls = None
                if cn:
                    for k, v in ic.items():
                        if v and k != "_all" and (norm(k) == cn or cn in norm(k) or norm(k) in cn):
                            urls = v
                            break
                if urls is None:
                    urls = ic.get("_all") or (next((v for v in ic.values() if v), []))
            return fetch(urls or [])

        variants = []
        seen = set()
        for rec in d["rows"]:
            car = rec["carat"]
            rcolours = [c["label"] for c in rec["colours"] if c["label"]] or [""]
            for colour in rcolours:
                sel = {}
                if any(colour_labels):
                    sel["Color"] = colour
                if multi_carat and car:
                    sel["Carat"] = car
                k = json.dumps(sel, sort_keys=True)
                if k in seen:
                    continue
                imset = imgs_for(rec, colour)
                if not imset:
                    continue
                seen.add(k)
                usd = rec["price_by_color"].get(colour) or rec["price_by_color"].get("_all") or rec["overall"]
                orig = rec["orig_by_color"].get(colour) or rec["orig_by_color"].get("_all")
                variants.append({
                    "sel": sel, "usd": usd, "orig": orig if orig and orig > (usd or 0) else None,
                    "imgs": [x["full"] for x in imset], "thumb": imset[0]["thumb"],
                })
        if not variants:
            continue

        options = []
        if any(colour_labels):
            options.append({"name": "Color", "type": "swatch",
                            "values": [{"label": c, "hex": d["colours"][c],
                                        "q": QCOLOR.get(c.lower().strip())} for c in colour_labels]})
        if multi_carat:
            options.append({"name": "Carat", "type": "select", "values": [{"label": c} for c in carats]})
        if len(d["sizes"]) >= 2:
            options.append({"name": "Size", "type": "select", "values": [{"label": s} for s in d["sizes"]]})

        materials = ["Lab Grown Diamond"]
        for c in colour_labels:
            mt = QMETAL.get(c.lower().strip())
            if mt and mt not in materials:
                materials.append(mt)
        out.append({"id": did, "cat": cat, "name": d["name"], "details": d["details"],
                    "rating": d["rating"], "reviews": d["reviews"], "materials": materials,
                    "options": options, "variants": variants})

    order = ["Engagement Rings", "Rings", "Necklaces", "Earrings", "Bracelets"]
    out.sort(key=lambda p: (order.index(p["cat"]) if p["cat"] in order else 99, p["name"].lower()))
    pathlib.Path("shopdata").mkdir(exist_ok=True)
    json.dump(out, open("shopdata/variants.json", "w", encoding="utf-8"), ensure_ascii=False)
    from collections import Counter
    print("designs:", len(out), dict(Counter(p["cat"] for p in out)))
    print("with carat option:", sum(1 for p in out for o in p["options"] if o["name"] == "Carat"))
    print("total variants:", sum(len(p["variants"]) for p in out))
    print("total images:", sum(len(v["imgs"]) for p in out for v in p["variants"]))


if __name__ == "__main__":
    main()
