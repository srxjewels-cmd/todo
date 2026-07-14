#!/usr/bin/env python3
r"""Build a shoppable "link in bio" landing page from scraped product folders.

Reads a folder like D:\quine p\prd (with category subfolders such as Rings,
Necklaces, each holding product folders that contain photos + info.txt), and
writes ONE self-contained index.html: a phone-friendly catalogue where every
product has an "Enquire on WhatsApp" button that opens a chat to YOUR number
with a message naming that exact piece (so you know what they mean).

Everything (images included, shrunk and embedded) is inside the single HTML
file, so you can open it directly or upload it anywhere for a bio link.

Setup once:  pip install pillow
Run:         python make_landing_page.py "D:\quine p\prd"
(defaults: brand SRX DIAMONDS, WhatsApp +91 9723891732 - override with --brand/--whatsapp)

The page is written to <root>\index.html.

[patched] Also supports folders where info.txt was renamed to the price
(e.g. "$3,300.00.txt"): products are found by their photos, and any .txt file
starting with "Product name:" is accepted as the info file.
"""

import argparse
import base64
import html
import io
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

SKIP_TXT = {"info.txt", "photo_urls.txt", "_summary.txt"}
CARD_WIDTH = 640          # embedded image width in px (keeps the file small)
JPEG_QUALITY = 72


def find_info_file(folder):
    info = folder / "info.txt"
    if info.exists():
        return info
    for f in sorted(folder.glob("*.txt")):
        if f.name.lower() in SKIP_TXT:
            continue
        try:
            head = f.read_text(encoding="utf-8", errors="ignore")[:200]
        except Exception:
            continue
        if head.lower().lstrip().startswith("product name:"):
            return f
    return None


def read_info(folder):
    name = price = url = ""
    info = find_info_file(folder)
    if info is not None:
        for line in info.read_text(encoding="utf-8", errors="ignore").splitlines():
            low = line.lower()
            if low.startswith("product name:"):
                name = line.split(":", 1)[1].strip()
            elif low.startswith("price:"):
                price = line.split(":", 1)[1].strip()
            elif low.startswith("url:"):
                url = line.split(":", 1)[1].strip()
    return name, price, url


def parse_price(s):
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def details_text(folder):
    info = find_info_file(folder)
    info_name = info.name.lower() if info is not None else ""
    for f in sorted(folder.glob("*.txt")):
        if f.name.lower() in SKIP_TXT or f.name.lower() == info_name:
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return ""
        # drop a leading header line that is just the section label
        lines = txt.splitlines()
        if lines and len(lines[0].split()) <= 3 and lines[0].isupper():
            lines = lines[1:]
        return "\n".join(l for l in lines if l.strip()).strip()
    return ""


def _photo_key(p):
    m = re.search(r"(\d+)", p.stem)
    return (0, int(m.group(1))) if m else (1, p.name)


def all_photos(folder, cap):
    pics = sorted(folder.glob("photo_*.jpg"), key=_photo_key) \
        + sorted(folder.glob("photo_*.png"), key=_photo_key)
    if not pics:
        pics = [f for f in sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
                if not f.name.lower().startswith("details")]
    return pics[:cap]


def embed_image(path, width=CARD_WIDTH, quality=JPEG_QUALITY):
    if path is None:
        return ""
    try:
        data = path.read_bytes()
    except Exception:
        return ""
    if Image is not None:
        try:
            with Image.open(io.BytesIO(data)) as im:
                im = im.convert("RGB")
                w, h = im.size
                if w > width:
                    im = im.resize((width, round(h * width / w)))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=quality, optimize=True)
                data = buf.getvalue()
        except Exception:
            pass
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


def strip_leading_number(name):
    return re.sub(r"^\s*\d+\s*[.\-)]\s*", "", name).strip()


def collect(root, max_photos=8):
    products = []
    seen_folders = set()
    # find product folders by their photos (works even if info.txt was renamed)
    for photo in sorted(root.rglob("photo_*.jpg")) + sorted(root.rglob("photo_*.png")):
        folder = photo.parent
        if folder == root or folder in seen_folders:
            continue
        seen_folders.add(folder)
        rel = folder.relative_to(root).parts
        category = rel[0] if len(rel) > 1 else "Jewelry"
        sub = rel[1] if len(rel) > 2 else ""
        if sub.isdigit():
            sub = ""
        cat_label = f"{category} · {sub}" if sub else category
        name, price, _url = read_info(folder)
        name = name or strip_leading_number(folder.name)
        pics = all_photos(folder, max_photos)
        imgs = [embed_image(pics[0])] if pics else []
        imgs += [embed_image(x, width=560, quality=62) for x in pics[1:]]
        imgs = [u for u in imgs if u]
        products.append({
            "cat": cat_label,
            "name": name,
            "price": price or "",
            "from": price.lower().startswith("from") if price else False,
            "num": parse_price(price),
            "imgs": imgs,
            "details": details_text(folder),
        })
    # stable ids + sort each category by price low->high
    products.sort(key=lambda p: (p["cat"].lower(), p["num"] is None, p["num"] or 0.0,
                                 p["name"].lower()))
    seen = {}
    for p in products:
        code = "".join(w[0] for w in re.findall(r"[A-Za-z]+", p["cat"])[:2]).upper() or "P"
        seen[code] = seen.get(code, 0) + 1
        p["id"] = f"{code}-{seen[code]:02d}"
        pr = p["price"]
        if p["from"]:
            pr = pr[4:].strip() if pr[:4].lower() == "from" else pr
        p["price_display"] = pr
    return products


TEMPLATE = r"""<title>__BRAND__ — Shop via WhatsApp</title>
<style>
  :root{
    --bg:#F0EEE9; --surface:#FBFAF7; --ink:#1B1A17; --muted:#726C61;
    --line:#E4E0D7; --gold:#8C6F35; --wa:#1FA855; --wa-ink:#FFFFFF;
    --shadow:0 1px 2px rgba(27,26,23,.04), 0 12px 30px -18px rgba(27,26,23,.28);
    --maxw:1120px; --r:14px;
  }
  @media (prefers-color-scheme:dark){:root{
      --bg:#141310; --surface:#1C1B15; --ink:#F1EDE4; --muted:#A39C8D;
      --line:#2C2A21; --gold:#C7A35C; --wa:#25D366; --wa-ink:#08130B;
      --shadow:0 1px 2px rgba(0,0,0,.4), 0 18px 40px -22px rgba(0,0,0,.7);}}
  :root[data-theme="light"]{--bg:#F0EEE9; --surface:#FBFAF7; --ink:#1B1A17; --muted:#726C61;
      --line:#E4E0D7; --gold:#8C6F35; --wa:#1FA855; --wa-ink:#FFFFFF;
      --shadow:0 1px 2px rgba(27,26,23,.04), 0 12px 30px -18px rgba(27,26,23,.28);}
  :root[data-theme="dark"]{--bg:#141310; --surface:#1C1B15; --ink:#F1EDE4; --muted:#A39C8D;
      --line:#2C2A21; --gold:#C7A35C; --wa:#25D366; --wa-ink:#08130B;
      --shadow:0 1px 2px rgba(0,0,0,.4), 0 18px 40px -22px rgba(0,0,0,.7);}
  *{box-sizing:border-box} html{-webkit-text-size-adjust:100%}
  body{margin:0; background:var(--bg); color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    line-height:1.5; -webkit-font-smoothing:antialiased;}
  a{color:inherit}
  .wrap{max-width:var(--maxw); margin:0 auto; padding:0 20px}
  header.site{padding:34px 20px 18px; text-align:center; border-bottom:1px solid var(--line)}
  .brand{font-family:Georgia,"Times New Roman",serif; font-weight:600;
    font-size:clamp(1.9rem,5.4vw,2.7rem); letter-spacing:.02em; margin:0; text-wrap:balance;}
  .rule{width:46px; height:1px; background:var(--gold); margin:14px auto 12px; opacity:.85}
  .tag{color:var(--muted); font-size:.95rem; margin:0 auto; max-width:54ch}
  .howto{margin:16px auto 2px; display:inline-flex; gap:8px; align-items:center; font-size:.8rem;
    color:var(--muted); border:1px solid var(--line); background:var(--surface); padding:7px 13px; border-radius:999px;}
  .howto b{color:var(--ink); font-weight:600}
  .filters{position:sticky; top:0; z-index:20; background:color-mix(in srgb,var(--bg) 88%, transparent);
    backdrop-filter:blur(8px); border-bottom:1px solid var(--line); padding:12px 0;}
  .filters .wrap{display:flex; gap:8px; overflow-x:auto; scrollbar-width:none}
  .filters .wrap::-webkit-scrollbar{display:none}
  .chip{flex:0 0 auto; border:1px solid var(--line); background:var(--surface); color:var(--muted);
    padding:8px 15px; border-radius:999px; font-size:.83rem; cursor:pointer; white-space:nowrap;
    transition:background .18s,color .18s,border-color .18s;}
  .chip[aria-pressed="true"]{background:var(--ink); color:var(--bg); border-color:var(--ink)}
  .chip:focus-visible{outline:2px solid var(--gold); outline-offset:2px}
  main{padding:26px 0 40px}
  .count{color:var(--muted); font-size:.82rem; text-transform:uppercase; letter-spacing:.12em; margin:0 0 16px}
  .grid{display:grid; gap:18px; grid-template-columns:repeat(auto-fill,minmax(215px,1fr));}
  .card{background:var(--surface); border:1px solid var(--line); border-radius:var(--r); overflow:hidden;
    display:flex; flex-direction:column; box-shadow:var(--shadow); transition:transform .2s ease;}
  .card:hover{transform:translateY(-3px)}
  .thumb{position:relative; aspect-ratio:4/5; width:100%; border:0; padding:0; cursor:zoom-in;
    background:#ddd; overflow:hidden; display:block;}
  .thumb img{width:100%; height:100%; object-fit:cover; display:block; transition:transform .5s ease}
  .card:hover .thumb img{transform:scale(1.045)}
  .ph{position:absolute; inset:0; display:grid; place-items:center; color:#fff;
    background:linear-gradient(150deg,#C9B79A,#8C7B63)}
  .ph svg{width:38%; max-width:120px; opacity:.9}
  .body{padding:13px 14px 15px; display:flex; flex-direction:column; gap:9px; flex:1}
  .eyebrow{font-size:.66rem; letter-spacing:.16em; text-transform:uppercase; color:var(--gold); font-weight:600}
  .name{font-family:Georgia,"Times New Roman",serif; font-size:1.02rem; line-height:1.3; margin:0}
  .price{font-size:.98rem; color:var(--ink); font-variant-numeric:tabular-nums; margin-top:-2px}
  .price .from{color:var(--muted); font-size:.78rem; margin-right:4px}
  .spacer{flex:1}
  .wa{display:inline-flex; align-items:center; justify-content:center; gap:8px; background:var(--wa);
    color:var(--wa-ink); text-decoration:none; font-weight:600; font-size:.9rem; padding:11px 12px;
    border-radius:10px; border:0; cursor:pointer; width:100%; transition:filter .15s;}
  .wa:hover{filter:brightness(1.05)}
  .wa:focus-visible{outline:2px solid var(--gold); outline-offset:2px}
  .wa svg{width:17px; height:17px; flex:0 0 auto}
  .lb{position:fixed; inset:0; z-index:60; display:none; place-items:center; padding:18px;
    background:rgba(15,14,11,.72); backdrop-filter:blur(3px)}
  .lb[open]{display:grid}
  .lb-card{background:var(--surface); border:1px solid var(--line); border-radius:16px; max-width:520px;
    width:100%; overflow:hidden; box-shadow:var(--shadow); max-height:92vh; display:flex; flex-direction:column}
  .lb-img{position:relative; aspect-ratio:1/1; background:#ccc}
  .lb-img img{width:100%; height:100%; object-fit:cover; display:block}
  .lb-body{padding:18px 20px 20px; overflow:auto}
  .lb-body h3{font-family:Georgia,serif; margin:.1rem 0; font-size:1.3rem}
  .lb-price{color:var(--gold); font-weight:600; margin:0 0 10px; font-variant-numeric:tabular-nums}
  .lb-details{white-space:pre-line; color:var(--muted); font-size:.9rem; margin:0 0 16px;
    border-top:1px solid var(--line); padding-top:12px}
  .close{position:absolute; top:10px; right:10px; z-index:2; width:34px; height:34px; border-radius:999px;
    border:0; background:rgba(0,0,0,.45); color:#fff; font-size:1.1rem; cursor:pointer; line-height:1}
  .nph{position:absolute; left:10px; bottom:10px; background:rgba(0,0,0,.5); color:#fff;
    font-size:.68rem; padding:3px 9px; border-radius:999px; pointer-events:none}
  .nav{position:absolute; top:50%; transform:translateY(-50%); z-index:2; width:36px; height:36px;
    border-radius:999px; border:0; background:rgba(0,0,0,.45); color:#fff; font-size:1.15rem;
    cursor:pointer; display:grid; place-items:center}
  .nav.prev{left:10px} .nav.next{right:10px}
  .lb-thumbs{display:flex; gap:6px; padding:10px 12px 0; overflow-x:auto; background:var(--surface)}
  .lb-thumbs img{width:52px; height:52px; object-fit:cover; border-radius:8px; opacity:.55;
    cursor:pointer; border:2px solid transparent; flex:0 0 auto}
  .lb-thumbs img[data-on]{opacity:1; border-color:var(--gold)}
  footer{border-top:1px solid var(--line); padding:26px 20px 40px; text-align:center; color:var(--muted); font-size:.85rem}
  footer .brand-sm{font-family:Georgia,serif; color:var(--ink); font-size:1.1rem}
  footer a{color:var(--gold); text-decoration:none}
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<header class="site">
  <h1 class="brand">__BRAND__</h1>
  <div class="rule"></div>
  <p class="tag">Tap any piece to enquire — we reply on WhatsApp.</p>
  <div class="howto">See something you like? <b>Tap “Enquire on WhatsApp”</b> — the piece is filled in for you.</div>
</header>
<nav class="filters" aria-label="Filter by category"><div class="wrap" id="chips"></div></nav>
<main class="wrap"><p class="count" id="count"></p><div class="grid" id="grid"></div></main>
<div class="lb" id="lb" role="dialog" aria-modal="true" aria-label="Product details">
  <div class="lb-card"><div class="lb-img"><button class="close" id="lbClose" aria-label="Close">✕</button>
      <button class="nav prev" id="lbPrev" aria-label="Previous photo">‹</button>
      <button class="nav next" id="lbNext" aria-label="Next photo">›</button>
      <div id="lbImg"></div></div>
    <div class="lb-thumbs" id="lbThumbs"></div>
    <div class="lb-body"><div class="eyebrow" id="lbCat"></div><h3 id="lbName"></h3>
      <p class="lb-price" id="lbPrice"></p><p class="lb-details" id="lbDetails"></p>
      <a class="wa" id="lbWa" href="#" target="_blank" rel="noopener"></a></div></div>
</div>
<footer><div class="brand-sm">__BRAND__</div>
  <p>Enquiries &amp; orders via WhatsApp · <a id="footWa" href="#" target="_blank" rel="noopener">Message us</a></p></footer>

<script>
  var WHATSAPP = "__WHATSAPP__";
  var BRAND    = "__BRAND__";
  var PRODUCTS = __PRODUCTS__;
  var GEM = '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"><path d="M20 8h24l12 14-24 34L8 22z"/><path d="M8 22h48M20 8l4 14 8 34 8-34 4-14"/></svg>';
  var WA_ICON = '<svg viewBox="0 0 32 32" fill="currentColor"><path d="M16 3C9 3 3.5 8.5 3.5 15.5c0 2.4.7 4.6 1.9 6.6L3 29l7.1-2.3c1.9 1 4 1.6 6.3 1.6h.1c6.9 0 12.5-5.6 12.5-12.5S23 3 16 3zm0 22.7c-2 0-3.9-.5-5.5-1.5l-.4-.2-4.2 1.4 1.4-4.1-.3-.4a10 10 0 01-1.6-5.4C5.4 9.9 10.2 5.3 16 5.3s10.6 4.6 10.6 10.2S21.8 25.7 16 25.7zm5.8-7.6c-.3-.2-1.9-.9-2.2-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a8.2 8.2 0 01-2.4-1.5 9 9 0 01-1.7-2.1c-.2-.3 0-.5.1-.7l.5-.6.3-.5c0-.2 0-.4 0-.6l-1-2.3c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.4-1.2 1.2-1.2 2.9s1.2 3.4 1.4 3.6c.2.2 2.5 3.8 6 5.3.8.4 1.5.6 2 .7.8.3 1.6.2 2.2.1.7-.1 1.9-.8 2.2-1.5.3-.8.3-1.4.2-1.5s-.3-.2-.6-.4z"/></svg>';
  function esc(s){return (s||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function waLink(p){
    var msg = "Hello " + BRAND + "! I'm interested in this piece:\n• " + p.name +
      (p.price_display ? " (" + (p.from?"from ":"") + p.price_display + ")" : "") +
      "\n• Ref: " + p.id + "\n\nIs it available?";
    return "https://wa.me/" + WHATSAPP + "?text=" + encodeURIComponent(msg);
  }
  function thumb(p){
    return (p.imgs && p.imgs.length)
      ? '<img loading="lazy" src="'+p.imgs[0]+'" alt="'+esc(p.name)+'">'
      : '<span class="ph">'+GEM+'</span>';
  }
  function badge(p){
    return (p.imgs && p.imgs.length>1) ? '<span class="nph">'+p.imgs.length+' photos</span>' : '';
  }
  var grid=document.getElementById("grid"), active="All";
  var cats=["All"].concat(PRODUCTS.map(function(p){return p.cat;}).filter(function(v,i,a){return a.indexOf(v)===i;}));
  function render(){
    var items=PRODUCTS.filter(function(p){return active==="All"||p.cat===active;});
    document.getElementById("count").textContent=items.length+" piece"+(items.length===1?"":"s");
    grid.innerHTML=items.map(function(p,i){
      return '<article class="card"><button class="thumb" data-i="'+PRODUCTS.indexOf(p)+'" aria-label="View '+esc(p.name)+'">'+thumb(p)+badge(p)+'</button>'+
        '<div class="body"><div class="eyebrow">'+esc(p.cat)+'</div><h3 class="name">'+esc(p.name)+'</h3>'+
        '<div class="price">'+(p.from?'<span class="from">from</span>':'')+esc(p.price_display||"Enquire")+'</div>'+
        '<div class="spacer"></div><a class="wa" href="'+waLink(p)+'" target="_blank" rel="noopener">'+WA_ICON+'Enquire on WhatsApp</a></div></article>';
    }).join("");
  }
  var chips=document.getElementById("chips");
  chips.innerHTML=cats.map(function(c){return '<button class="chip" aria-pressed="'+(c==="All")+'" data-cat="'+esc(c)+'">'+esc(c)+'</button>';}).join("");
  chips.addEventListener("click",function(e){var b=e.target.closest(".chip");if(!b)return;active=b.dataset.cat;
    [].forEach.call(chips.children,function(c){c.setAttribute("aria-pressed",c===b);});render();});
  var lb=document.getElementById("lb"), lbP=null, lbCur=0;
  function lbShow(i){
    if(!lbP||!lbP.imgs||!lbP.imgs.length)return;
    var n=lbP.imgs.length; lbCur=(i%n+n)%n;
    document.getElementById("lbImg").innerHTML='<img src="'+lbP.imgs[lbCur]+'" alt="'+esc(lbP.name)+'">';
    [].forEach.call(document.getElementById("lbThumbs").children,function(t,j){
      if(j===lbCur)t.setAttribute("data-on","");else t.removeAttribute("data-on");});
  }
  function openLb(p){
    lbP=p; lbCur=0;
    var multi=p.imgs&&p.imgs.length>1;
    var strip=document.getElementById("lbThumbs");
    strip.innerHTML=multi?p.imgs.map(function(u,j){return '<img src="'+u+'" data-j="'+j+'" alt="">';}).join(""):"";
    strip.style.display=multi?"flex":"none";
    document.getElementById("lbPrev").style.display=multi?"grid":"none";
    document.getElementById("lbNext").style.display=multi?"grid":"none";
    if(p.imgs&&p.imgs.length)lbShow(0);else document.getElementById("lbImg").innerHTML=thumb(p);
    document.getElementById("lbCat").textContent=p.cat;document.getElementById("lbName").textContent=p.name;
    document.getElementById("lbPrice").textContent=(p.price_display?(p.from?"from ":"")+p.price_display:"Enquire for price");
    var d=document.getElementById("lbDetails");d.textContent=p.details||"";d.style.display=(p.details||"").trim()?"block":"none";
    var wa=document.getElementById("lbWa");wa.href=waLink(p);wa.innerHTML=WA_ICON+"Enquire about this piece";lb.setAttribute("open","");}
  document.getElementById("lbPrev").addEventListener("click",function(e){e.stopPropagation();lbShow(lbCur-1);});
  document.getElementById("lbNext").addEventListener("click",function(e){e.stopPropagation();lbShow(lbCur+1);});
  document.getElementById("lbThumbs").addEventListener("click",function(e){
    var t=e.target.closest("img[data-j]");if(t)lbShow(+t.dataset.j);});
  (function(){var x0=null;var im=document.getElementById("lbImg");
    im.addEventListener("touchstart",function(e){x0=e.touches[0].clientX;},{passive:true});
    im.addEventListener("touchend",function(e){if(x0===null)return;
      var dx=e.changedTouches[0].clientX-x0;x0=null;
      if(Math.abs(dx)>40)lbShow(lbCur+(dx<0?1:-1));},{passive:true});})();
  document.addEventListener("keydown",function(e){
    if(!lb.hasAttribute("open"))return;
    if(e.key==="ArrowRight")lbShow(lbCur+1);
    if(e.key==="ArrowLeft")lbShow(lbCur-1);});
  grid.addEventListener("click",function(e){var t=e.target.closest(".thumb");if(!t)return;openLb(PRODUCTS[+t.dataset.i]);});
  document.getElementById("lbClose").addEventListener("click",function(){lb.removeAttribute("open");});
  lb.addEventListener("click",function(e){if(e.target===lb)lb.removeAttribute("open");});
  document.addEventListener("keydown",function(e){if(e.key==="Escape")lb.removeAttribute("open");});
  document.getElementById("footWa").href="https://wa.me/"+WHATSAPP+"?text="+encodeURIComponent("Hello "+BRAND+"! I have a question about your jewelry.");
  render();
</script>
"""


def build_html(products, brand, whatsapp):
    payload = [{
        "id": p["id"], "cat": p["cat"], "name": p["name"],
        "price_display": p["price_display"], "from": p["from"],
        "imgs": p["imgs"], "details": p["details"],
    } for p in products]
    return (TEMPLATE
            .replace("__PRODUCTS__", json.dumps(payload, ensure_ascii=False))
            .replace("__WHATSAPP__", re.sub(r"\D", "", whatsapp))
            .replace("__BRAND__", html.escape(brand)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=r"D:\quine p\prd")
    ap.add_argument("--whatsapp", default="919723891732",
                    help="your WhatsApp number, country code + digits, e.g. 9198XXXXXXXX")
    ap.add_argument("--brand", default="SRX DIAMONDS")
    ap.add_argument("--out", default="", help="output html path (default <root>\\index.html)")
    ap.add_argument("--max-photos-per-product", type=int, default=8,
                    help="cap on embedded photos per product (default 8)")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"Folder not found:\n  {root}")
        return 1
    if Image is None:
        print("Note: Pillow not installed - images will be embedded full-size "
              "(bigger file). Run 'pip install pillow' for smaller output.\n")
    if not re.sub(r"\D", "", args.whatsapp):
        print("Tip: pass --whatsapp <your number> so the buttons message you. "
              "Building with a placeholder for now.\n")

    print(f"Scanning {root} ...")
    products = collect(root, max_photos=args.max_photos_per_product)
    if not products:
        print("No products found (need subfolders with info.txt / photos).")
        return 1
    html_out = build_html(products, args.brand, args.whatsapp or "919723891732")
    out = Path(args.out) if args.out else (root / "index.html")
    out.write_text(html_out, encoding="utf-8")
    mb = out.stat().st_size / 1048576
    cats = sorted({p["cat"] for p in products})
    total_imgs = sum(len(p["imgs"]) for p in products)
    nodet = [p["name"] for p in products if not (p["details"] or "").strip()]
    print(f"\nDone: {len(products)} products across {len(cats)} categories "
          f"({total_imgs} photos embedded).")
    print("Categories: " + ", ".join(cats))
    if nodet:
        print(f"Products with no details text ({len(nodet)}): "
              + ", ".join(nodet[:8]) + (" ..." if len(nodet) > 8 else ""))
    print(f"Page written to: {out}  ({mb:.1f} MB)")
    print("\nOpen it to preview. To use as a bio link, upload index.html to any "
          "free host\n(e.g. drag it onto https://app.netlify.com/drop) and put "
          "that link in your bio.")
    return 0


if __name__ == "__main__":
    rc = main()
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass
    sys.exit(rc)
