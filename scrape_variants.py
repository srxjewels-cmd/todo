#!/usr/bin/env python3
r"""Scrape Quince lab-grown-diamond jewelry into a variant catalog.

For each category it finds product pages, reads each product's __NEXT_DATA__
(colours+hex, size options, price, per-colour images, details HTML, and the
carat from the slug/title), then groups sibling pages by base design into
variant products for build_variant_shop.py:

  design = one card with Color swatches + Carat + Size options; each
  (colour x carat x size) variant carries its price and that colour's photos.

Images are downloaded + resized under docs/photos/<designId>/<n>.jpg and
referenced by relative path. Writes shopdata/variants.json and docs/index.html.
"""
import re, io, json, time, html as htmlmod, pathlib, sys
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


def get(url):
    for a in (1, 2, 3):
        try:
            r = S.get(url, timeout=45)
            if r.ok:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(1.5 * a)
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
    val = m.group(1).rstrip(".")
    return f"{val}ctw"


def strip_variant_bits(title):
    t = re.sub(r"\s+in\s+(%s)\s*$" % "|".join(map(re.escape, COLORS)), "", title, flags=re.I)
    t = CARAT_RE.sub("", t)
    t = re.sub(r"[-–]\s*$", "", t).strip(" -–")
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


def vprice(v):
    pr = v.get("price")
    return pr.get("amount") if isinstance(pr, dict) else pr


def scrape_product(slug):
    h = get("https://www.quince.com/women/" + slug)
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
            nm = o.get("name")
            val = o.get("value")
            if nm and nm != "Color" and val and val != "One Size" and val not in sizes:
                sizes.append(val)
    price = None
    for v in variants:
        a = vprice(v)
        if a is not None:
            price = a if price is None else min(price, a)
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
            "price": price, "imgs_by_color": imgs_by_color,
            "details": clean_details(p.get("details", "")), "carat": carat_of(title, slug)}


def download(url, dest_full, dest_thumb):
    try:
        r = S.get(url + ("&" if "?" in url else "?") + "w=1600", timeout=45)
        if not (r.ok and r.content):
            r = S.get(url, timeout=45)
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return False
    w, h = im.size
    if w > 1600:
        im = im.resize((1600, round(h * 1600 / w)))
    im.save(dest_full, "JPEG", quality=85, optimize=True)
    w, h = im.size
    tw = min(700, w)
    im.resize((tw, round(h * tw / w))).save(dest_thumb, "JPEG", quality=78, optimize=True)
    return True


def main():
    photos = pathlib.Path("docs/photos")
    photos.mkdir(parents=True, exist_ok=True)
    designs = {}   # (cat, base) -> design dict
    dcount = 0
    for cat, url in CATS.items():
        slugs = category_slugs(url)
        print(f"[{cat}] {len(slugs)} product slugs", flush=True)
        for slug in slugs:
            rec = scrape_product(slug)
            if not rec or rec["price"] is None:
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
                                    "details": "", "rows": []}
            for c in rec["colours"]:
                if c["label"] and c["label"] not in d["colours"]:
                    d["colours"][c["label"]] = c["hex"]
            car = rec["carat"]
            if car and car not in d["carats"]:
                d["carats"].append(car)
            for s in rec["sizes"]:
                if s not in d["sizes"]:
                    d["sizes"].append(s)
            if rec["details"] and len(rec["details"]) > len(d["details"]):
                d["details"] = rec["details"]
            d["rows"].append(rec)
        time.sleep(0.5)

    # assemble variant products + download images
    out = []
    for (cat, base), d in designs.items():
        did = d["id"]
        colour_imgs = {}     # colour label -> [rel paths]
        # gather images per colour across rows
        raw_by_color = {}
        for rec in d["rows"]:
            for ck, urls in rec["imgs_by_color"].items():
                raw_by_color.setdefault(ck, [])
                for u in urls:
                    if u not in raw_by_color[ck]:
                        raw_by_color[ck].append(u)
        # download (cap 8/colour)
        for ck, urls in raw_by_color.items():
            safe = re.sub(r"[^a-z0-9]+", "-", ck.lower()).strip("-") or "all"
            folder = photos / did / safe
            folder.mkdir(parents=True, exist_ok=True)
            rels = []
            n = 0
            for u in urls[:8]:
                n += 1
                full = folder / f"{n}.jpg"
                thumb = folder / f"{n}_t.jpg"
                if download(u, full, thumb):
                    rels.append({"full": f"photos/{did}/{safe}/{n}.jpg",
                                 "thumb": f"photos/{did}/{safe}/{n}_t.jpg"})
            colour_imgs[ck] = rels
        colour_labels = list(d["colours"].keys())
        options = []
        if len(colour_labels) >= 1 and any(colour_labels):
            options.append({"name": "Color", "type": "swatch",
                            "values": [{"label": c, "hex": d["colours"][c]} for c in colour_labels]})
        carats = sorted(d["carats"], key=lambda x: float(re.sub(r"[^\d.]", "", x) or 0))
        if len(carats) >= 2:
            options.append({"name": "Carat", "type": "select",
                            "values": [{"label": c} for c in carats]})
        if len(d["sizes"]) >= 2:
            options.append({"name": "Size", "type": "select",
                            "values": [{"label": s} for s in d["sizes"]]})

        def norm(s):
            return re.sub(r"1[048]k|[^a-z0-9]", "", s.lower())

        def imgs_for(colour):
            if colour_imgs.get(colour):
                return colour_imgs[colour]
            cn = norm(colour)
            if cn:
                for k, v in colour_imgs.items():
                    if v and k not in ("_all",) and (norm(k) == cn or cn in norm(k) or norm(k) in cn):
                        return v
            if colour_imgs.get("_all"):
                return colour_imgs["_all"]
            for v in colour_imgs.values():
                if v:
                    return v
            return []

        variants = []
        for rec in d["rows"]:
            car = rec["carat"]
            rcolours = [c["label"] for c in rec["colours"] if c["label"]] or [""]
            for colour in rcolours:
                imset = imgs_for(colour)
                sel = {}
                if any(colour_labels):
                    sel["Color"] = colour
                if len(carats) >= 2 and car:
                    sel["Carat"] = car
                variants.append({
                    "sel": sel, "usd": rec["price"], "from": False,
                    "imgs": [x["full"] for x in imset],
                    "thumb": imset[0]["thumb"] if imset else "",
                })
        # dedupe variants by sel (keep first)
        seen = set()
        uniq = []
        for v in variants:
            k = json.dumps(v["sel"], sort_keys=True)
            if k in seen:
                continue
            seen.add(k)
            if v["imgs"]:
                uniq.append(v)
        if not uniq:
            continue
        out.append({"id": did, "cat": cat, "name": d["name"], "details": d["details"],
                    "options": options, "variants": uniq})

    order = ["Engagement Rings", "Rings", "Necklaces", "Earrings", "Bracelets"]
    out.sort(key=lambda p: (order.index(p["cat"]) if p["cat"] in order else 99, p["name"].lower()))
    pathlib.Path("shopdata").mkdir(exist_ok=True)
    json.dump(out, open("shopdata/variants.json", "w", encoding="utf-8"), ensure_ascii=False)
    from collections import Counter
    print("designs:", len(out), dict(Counter(p["cat"] for p in out)))
    print("total variants:", sum(len(p["variants"]) for p in out))
    print("total images:", sum(len(v["imgs"]) for p in out for v in p["variants"]))


if __name__ == "__main__":
    main()
