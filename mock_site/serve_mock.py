#!/usr/bin/env python3
"""Offline mock of Quince's page structures, for end-to-end testing quince_scraper.py.

Mirrors the DOM patterns the scraper relies on:
  * category grid tiles: image + heading link with ?color=..., price in the card
  * recommendation-carousel links carrying tracker= (must be excluded)
  * subcollection tile linking back to the category itself (must be excluded)
  * product gallery: thumbnail rail (one lazy via data-src, one duplicate image),
    main image with srcset, a 1x1 tracking pixel, a small icon
  * DETAILS accordion, both collapsed (button + aria-expanded) and pre-expanded (div)
  * a product link that 404s, to exercise failure handling

Usage:
    python mock_site/serve_mock.py --root /tmp/mockroot --port 8765
then:
    python quince_scraper.py --category-url http://127.0.0.1:8765/category.html \
        --out ./mock_out --limit 3 --headless --image-host 127.0.0.1 \
        --min-delay 0.3 --max-delay 0.5 --no-proxy-env
"""

import argparse
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw

CATEGORY = """<!doctype html>
<html><head><title>Mock Lab Grown Diamond Necklaces</title></head>
<body>
<header><nav><a href="/category.html">Home</a> <a href="/other.html">Women</a></nav></header>
<h1>Lab Grown Diamond Necklaces</h1>
<p>3 items</p>
<div class="subtiles"><a href="/category.html"><img src="/assets/icon.jpg" width="80"><h2>All</h2></a></div>
<main>
 <div class="tile">
   <a href="/p1.html?color=yellow-gold"><img src="/assets/p1_a.jpg?w=662&q=50&h=828" width="300"></a>
   <h2><a href="/p1.html?color=yellow-gold">Mock Bar Necklace</a></h2>
   <div class="price">$398.00</div>
 </div>
 <div class="tile">
   <a href="/p2.html?color=white-gold"><img src="/assets/p2_a.jpg?w=662&q=50&h=828" width="300"></a>
   <h2><a href="/p2.html?color=white-gold">Mock Tennis Necklace 7ctw</a></h2>
   <div class="price">From<br>$3,700.00</div>
 </div>
 <div class="tile">
   <a href="/p3.html?color=yellow-gold"><img src="/assets/p1_b.jpg?w=662&q=50&h=828" width="300"></a>
   <h2><a href="/p3.html?color=yellow-gold">Mock Missing Product</a></h2>
   <div class="price">$498.00</div>
 </div>
</main>
<section class="recs"><h3>Shoppers also love</h3>
 <div class="tile">
   <a href="/p2.html?color=yellow-gold&gender=women&tracker=collection_page__rec__0"><img src="/assets/p2_b.jpg?w=662" width="200"></a>
   <h2><a href="/p2.html?color=yellow-gold&tracker=collection_page__rec__0">Rec Item</a></h2>
   <div>$58.00</div>
 </div>
</section>
<footer><a href="/faq.html">FAQ</a></footer>
</body></html>
"""

P1 = """<!doctype html>
<html><head><title>Mock Bar Necklace</title>
<style>
.thumbs img{width:70px;height:88px;object-fit:cover;display:block;margin:4px}
.main img{width:560px} section.acc{width:520px;border-top:1px solid #999;padding:6px}
.pdp{display:flex;gap:24px}
</style></head>
<body>
<header><nav><a href="/category.html">Back to category</a></nav></header>
<div class="pdp">
 <div class="gallery">
  <div class="thumbs">
    <img src="/assets/p1_a.jpg?w=200&q=50&h=250">
    <img src="/assets/p1_b.jpg?w=200&q=50&h=250">
    <img data-src="/assets/p1_c.jpg?w=200&q=50&h=250" width="70">
    <img src="/assets/p1_d.jpg?w=200&q=50&h=250">
  </div>
  <div class="main"><img src="/assets/p1_a.jpg?w=800&q=50"
       srcset="/assets/p1_a.jpg?w=800&q=50 800w, /assets/p1_a.jpg?w=1600&q=50 1600w"></div>
  <img src="/assets/pixel.jpg" width="1" height="1">
  <img src="/assets/icon.jpg" width="90">
 </div>
 <div class="buy">
  <h1>Mock Bar Necklace</h1>
  <div>(12 REVIEWS)</div>
  <div class="price">$398.00</div>
  <div>You save 50% <s>$805.00</s> Traditional retail</div>
  <div>Color: Yellow Gold</div>
  <button>ADD TO BAG</button>
  <section class="acc">
    <button aria-expanded="false"
      onclick="var p=document.getElementById('pnl');var open=this.getAttribute('aria-expanded')==='true';this.setAttribute('aria-expanded',String(!open));p.style.display=open?'none':'block';">
      <span>Details</span></button>
    <div id="pnl" style="display:none">
      <ul><li>Crafted from 14K gold</li><li>Round lab grown diamonds</li>
      <li>Total carat weight: 0.50</li><li>Length: adjustable 16&quot;-18&quot;</li></ul>
    </div>
  </section>
  <section class="acc">
    <button aria-expanded="false"><span>Care</span></button>
    <div style="display:none">Care instructions text.</div>
  </section>
 </div>
</div>
<section class="recs"><h3>Style it with</h3>
  <a href="/p2.html?color=white-gold&tracker=pdp_rec"><img src="/assets/p2_a.jpg?w=662" width="180"></a>
</section>
</body></html>
"""

P2 = """<!doctype html>
<html><head><title>Mock Tennis Necklace</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Mock Tennis Necklace 7ctw",
 "image":["/assets/p2_a.jpg"],
 "offers":{"@type":"Offer","price":"3700.00","priceCurrency":"USD"}}
</script>
<style>.thumbs img{width:70px;display:block;margin:4px}.main img{width:560px}
.accwrap{width:520px;border-top:1px solid #999;padding:6px}</style>
</head><body>
<header><nav><a href="/category.html">Back</a></nav></header>
<h1>Mock Tennis Necklace 7ctw</h1>
<div>(4 REVIEWS)</div>
<div>From<br>$3,700.00</div>
<div class="gallery">
 <div class="thumbs">
  <img src="/assets/p2_a.jpg?w=200&q=50&h=250">
  <img src="/assets/p2_b.jpg?w=200&q=50&h=250">
  <img src="/assets/p2_c.jpg?w=200&q=50&h=250">
 </div>
 <div class="main"><img src="/assets/p2_a.jpg?w=1600&q=50"></div>
</div>
<div class="accwrap">
  <div class="acc-h">DETAILS</div>
  <div class="acc-p"><ul><li>14K gold</li><li>7ctw lab grown diamonds</li>
  <li>Color: FG, Clarity: VS2</li></ul></div>
</div>
</body></html>
"""


CATEGORY_G = """<!doctype html>
<html><head><title>Generic Shop - Rings</title></head>
<body>
<header><nav><a href="/category_g.html">Rings</a> <a href="/about.html">About</a></nav></header>
<h1>Rings</h1>
<main>
 <div class="card">
   <a href="/g1.html"><img src="/assets/gp1_a.jpg" width="280"></a>
   <h3><a href="/g1.html">Generic Solitaire Ring</a></h3>
   <span class="price">$129.00</span>
 </div>
 <div class="card">
   <a href="/g2.html"><img src="/assets/gp2_a_200x.jpg" width="280"></a>
   <h3><a href="/g2.html">Shopify-style Band Ring</a></h3>
   <span class="price">$89.00</span>
 </div>
</main>
<footer><a href="/faq.html">FAQ</a></footer>
</body></html>
"""

G1 = """<!doctype html>
<html><head><title>Generic Solitaire Ring</title>
<style>.thumbs img{width:64px;display:block;margin:4px}.main img{width:540px}
details{width:500px;border-top:1px solid #888;padding:6px}</style>
</head><body>
<header><nav><a href="/category_g.html">Back</a></nav></header>
<h1>Generic Solitaire Ring</h1>
<div>$129.00</div>
<div class="pdp">
 <div class="thumbs">
  <img src="/assets/gp1_a.jpg">
  <img src="/assets/gp1_b.jpg">
  <img src="/assets/gp1_c.jpg">
 </div>
 <div class="main"><img src="/assets/gp1_a.jpg"></div>
</div>
<details>
  <summary>Details</summary>
  <ul><li>925 sterling silver</li><li>1ct round stone</li><li>Sizes 5-9</li></ul>
</details>
</body></html>
"""

G2 = """<!doctype html>
<html><head><title>Shopify-style Band Ring</title>
<style>.thumbs img{width:64px;display:block;margin:4px}.main img{width:540px}
.desc{width:500px;border-top:1px solid #888;padding:6px}</style>
</head><body>
<header><nav><a href="/category_g.html">Back</a></nav></header>
<h1>Shopify-style Band Ring</h1>
<div>$89.00</div>
<div class="pdp">
 <div class="thumbs">
  <img src="/assets/gp2_a_200x.jpg">
  <img src="/assets/gp2_b_200x.jpg">
 </div>
 <div class="main"><img src="/assets/gp2_a_800x.jpg"></div>
</div>
<div class="desc">
  <div class="desc-h">DESCRIPTION</div>
  <div class="desc-p"><ul><li>14k gold vermeil band</li><li>3mm width</li>
  <li>Hypoallergenic</li></ul></div>
</div>
</body></html>
"""


def make_img(path, label, size=(1200, 1500), color=(210, 190, 160)):
    im = Image.new("RGB", size, color)
    if min(size) >= 400:
        d = ImageDraw.Draw(im)
        for x in range(0, size[0], 120):
            d.line([(x, 0), (x, size[1])], fill=(255, 255, 255), width=2)
        d.rectangle([40, 40, size[0] - 40, 160], fill=(255, 255, 255))
        d.text((60, 80), label, fill=(20, 20, 20))
    im.save(path, "JPEG", quality=88)


def build(root: Path):
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    make_img(assets / "p1_a.jpg", "P1 view A (main)", color=(214, 192, 158))
    make_img(assets / "p1_b.jpg", "P1 view B", color=(190, 205, 214))
    make_img(assets / "p1_c.jpg", "P1 view C (lazy data-src)", color=(205, 214, 190))
    shutil.copyfile(assets / "p1_a.jpg", assets / "p1_d.jpg")  # duplicate content
    make_img(assets / "p2_a.jpg", "P2 view A (main)", color=(222, 214, 202))
    make_img(assets / "p2_b.jpg", "P2 view B", color=(202, 214, 222))
    make_img(assets / "p2_c.jpg", "P2 view C", color=(214, 202, 222))
    make_img(assets / "icon.jpg", "icon", size=(120, 120))
    make_img(assets / "pixel.jpg", "", size=(1, 1))
    # Generic site: full-size originals plus Shopify-style resized copies
    # (real small files, so a failed suffix-strip shows up as tiny photos).
    make_img(assets / "gp1_a.jpg", "G1 ring view A", color=(200, 200, 220))
    make_img(assets / "gp1_b.jpg", "G1 ring view B", color=(220, 200, 200))
    make_img(assets / "gp1_c.jpg", "G1 ring view C", color=(200, 220, 200))
    make_img(assets / "gp2_a.jpg", "G2 band view A", color=(230, 210, 190))
    make_img(assets / "gp2_b.jpg", "G2 band view B", color=(190, 210, 230))
    for stem in ("gp2_a", "gp2_b"):
        make_img(assets / f"{stem}_200x.jpg", "", size=(200, 250))
    make_img(assets / "gp2_a_800x.jpg", "", size=(800, 1000))
    (root / "category.html").write_text(CATEGORY, encoding="utf-8")
    (root / "p1.html").write_text(P1, encoding="utf-8")
    (root / "p2.html").write_text(P2, encoding="utf-8")
    # p3.html intentionally missing -> 404 -> exercises the failure path
    (root / "category_g.html").write_text(CATEGORY_G, encoding="utf-8")
    (root / "g1.html").write_text(G1, encoding="utf-8")
    (root / "g2.html").write_text(G2, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    root = Path(args.root)
    build(root)
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Mock Quince serving {root} at http://127.0.0.1:{args.port}/category.html",
          flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
