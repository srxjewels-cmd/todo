#!/usr/bin/env python3
r"""Generate a PLACEHOLDER sample catalog + photos for the SRX storefront engine.

This creates fake, self-drawn products so you can see the exact data format the
storefront reads. Nothing here is scraped — the images are generated on the fly.

  1) python catalog/make_sample.py
       -> writes catalog/sample_catalog.json and catalog/photos/...
  2) python build_quince_shop.py catalog/sample_catalog.json \
         --out catalog/index.html --brand "SRX DIAMONDS" --whatsapp 919723891732
       -> open catalog/index.html

To make it YOUR store: edit sample_catalog.json (or produce the same JSON from
your own data), drop YOUR product photos in place of the placeholders, rebuild.
See catalog/README.md for the field-by-field format.
"""
import json, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
TINT = {"Yellow Gold": (232, 198, 110), "White Gold": (226, 226, 230),
        "Platinum": (214, 214, 222), "Rose Gold": (230, 183, 169)}
Q = {"Yellow Gold": "Yellow", "White Gold": "White", "Platinum": "Grey", "Rose Gold": "Pink"}
HEX = {"Yellow Gold": "#E6C46A", "White Gold": "#E5E5E8", "Platinum": "#D8D8DE", "Rose Gold": "#E6B7A9"}
MAT = {"Yellow Gold": "14k Gold", "White Gold": "14k Gold", "Rose Gold": "14k Gold", "Platinum": "Platinum"}


def placeholder(path, lines, tint, big):
    W = H = 1000 if big else 420
    im = Image.new("RGB", (W, H), (246, 244, 240))
    d = ImageDraw.Draw(im)
    r = W // 4
    cy = H // 2 - W // 14
    d.ellipse([W // 2 - r, cy - r, W // 2 + r, cy + r], outline=tint, width=max(8, W // 42))
    d.ellipse([W // 2 - r // 6, cy - r - W // 22, W // 2 + r // 6, cy - r + W // 9],
              outline=(150, 150, 160), width=max(3, W // 110))
    ty = cy + r + W // 28
    for ln in [l for l in lines if l]:
        try:
            w = d.textlength(ln)
        except Exception:
            w = len(ln) * 6
        d.text(((W - w) / 2, ty), ln, fill=(92, 86, 76))
        ty += W // 42
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "JPEG", quality=85)


def design(pid, cat, name, details, rating, reviews, colors, carats, carat_name, sizes, base, step, orig_mult):
    opts = [{"name": "Color", "type": "swatch",
             "values": [{"label": c, "hex": HEX[c], "q": Q[c]} for c in colors]}]
    if len(carats) >= 2:
        opts.append({"name": carat_name, "type": "select", "values": [{"label": str(c)} for c in carats]})
    if sizes:
        opts.append({"name": "Size", "type": "select", "values": [{"label": str(s)} for s in sizes]})
    variants = []
    for c in colors:
        cslug = c.lower().replace(" ", "-")
        for k, car in enumerate(carats):
            sel = {"Color": c}
            if len(carats) >= 2:
                sel[carat_name] = str(car)
            usd = int(base + step * k)
            orig = int(usd * orig_mult)
            folder = "photos/%s/%s-%s" % (pid, cslug, str(car).replace(".", "_"))
            imgs = ["%s/%d.jpg" % (folder, n) for n in (1, 2)]
            for n, rel in enumerate(imgs, 1):
                placeholder(os.path.join(HERE, rel),
                            [name[:22], c, ("%s: %sct" % (carat_name, car)) if len(carats) >= 2 else "", "View %d" % n],
                            TINT[c], True)
                placeholder(os.path.join(HERE, rel.replace(".jpg", "_t.jpg")), [c, "%sct" % car], TINT[c], False)
            variants.append({"sel": sel, "usd": usd, "orig": orig,
                             "imgs": imgs, "thumb": imgs[0].replace(".jpg", "_t.jpg")})
    materials = ["Lab Grown Diamond"] + sorted(set(MAT[c] for c in colors))
    return {"id": pid, "cat": cat, "name": name, "details": details,
            "rating": rating, "reviews": reviews, "materials": materials,
            "options": opts, "variants": variants}


RING_SIZES = [4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10]
catalog = [
    design("SRX-001", "Engagement Rings", "Round Solitaire Engagement Ring",
           "- Lab grown diamond, D-F colour, VS clarity\n- Solid 14K gold or platinum band\n"
           "- Center Carat Weight selectable 1-3 ct\n- Handcrafted; ships in 2-3 weeks",
           4.9, 214, ["Yellow Gold", "White Gold", "Platinum"], [1, 1.5, 2, 3],
           "Center Carat Weight", RING_SIZES, 1200, 900, 2.4),
    design("SRX-002", "Necklaces", "Lab Grown Diamond Tennis Necklace",
           "- Continuous line of lab grown diamonds\n- 14K gold, secure box clasp\n"
           "- Total carat weight selectable\n- 16\" length",
           4.8, 96, ["Yellow Gold", "White Gold"], [3, 5, 7], "Carat", [], 1900, 700, 2.5),
    design("SRX-003", "Earrings", "Lab Grown Diamond Solitaire Studs",
           "- Classic four-prong studs\n- 14K gold, screw-back posts\n- Sold as a pair",
           5.0, 41, ["Yellow Gold", "White Gold"], [1, 2], "Center Carat Weight", [], 700, 600, 2.3),
]
json.dump(catalog, open(os.path.join(HERE, "sample_catalog.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote sample_catalog.json:", len(catalog), "products,",
      sum(len(p["variants"]) for p in catalog), "variants,",
      sum(len(v["imgs"]) for p in catalog for v in p["variants"]) * 2, "image files")


if __name__ == "__main__":
    pass
