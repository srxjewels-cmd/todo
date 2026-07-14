#!/usr/bin/env python3
r"""Build a variant-aware shop page from a variants JSON.

Input JSON: list of products, each:
  {
    "id","cat","name","details",
    "options":[ {"name":"Color","type":"swatch",
                 "values":[{"label":"Yellow Gold","hex":"#E6C46A"}, ...]},
                {"name":"Carat","type":"select","values":[{"label":"1ctw"},...]} ],
    "variants":[ {"sel":{"Color":"Yellow Gold","Carat":"1ctw"},
                  "usd":698,"from":false,"imgs":["photos/.../1.jpg",...],
                  "thumb":"photos/.../1_t.jpg"}, ... ]
  }

Products with a single variant and no options render as plain cards.
Colour swatches + option dropdowns in the lightbox switch the photos, price
and WhatsApp reference. Includes the same geo-currency + WhatsApp features.
"""
import argparse, html, json, re, sys
from pathlib import Path

TEMPLATE = r"""<title>__BRAND__ — Shop via WhatsApp</title>
<style>
  :root{--bg:#F0EEE9;--surface:#FBFAF7;--ink:#1B1A17;--muted:#726C61;--line:#E4E0D7;
    --gold:#8C6F35;--wa:#1FA855;--wa-ink:#fff;--shadow:0 1px 2px rgba(27,26,23,.04),0 12px 30px -18px rgba(27,26,23,.28);--maxw:1120px;--r:14px;}
  @media (prefers-color-scheme:dark){:root{--bg:#141310;--surface:#1C1B15;--ink:#F1EDE4;--muted:#A39C8D;--line:#2C2A21;--gold:#C7A35C;--wa:#25D366;--wa-ink:#08130B;--shadow:0 1px 2px rgba(0,0,0,.4),0 18px 40px -22px rgba(0,0,0,.7);}}
  :root[data-theme="light"]{--bg:#F0EEE9;--surface:#FBFAF7;--ink:#1B1A17;--muted:#726C61;--line:#E4E0D7;--gold:#8C6F35;--wa:#1FA855;--wa-ink:#fff;}
  :root[data-theme="dark"]{--bg:#141310;--surface:#1C1B15;--ink:#F1EDE4;--muted:#A39C8D;--line:#2C2A21;--gold:#C7A35C;--wa:#25D366;--wa-ink:#08130B;}
  *{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
  .wrap{max-width:var(--maxw);margin:0 auto;padding:0 20px}
  header.site{padding:34px 20px 18px;text-align:center;border-bottom:1px solid var(--line)}
  .brand{font-family:Georgia,"Times New Roman",serif;font-weight:600;font-size:clamp(1.9rem,5.4vw,2.7rem);letter-spacing:.02em;margin:0}
  .rule{width:46px;height:1px;background:var(--gold);margin:14px auto 12px;opacity:.85}
  .tag{color:var(--muted);font-size:.95rem;margin:0 auto;max-width:54ch}
  .filters{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:12px 0}
  .filters .wrap{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none}.filters .wrap::-webkit-scrollbar{display:none}
  .chip{flex:0 0 auto;border:1px solid var(--line);background:var(--surface);color:var(--muted);padding:8px 15px;border-radius:999px;font-size:.83rem;cursor:pointer;white-space:nowrap}
  .chip[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
  main{padding:26px 0 40px}
  .count{color:var(--muted);font-size:.82rem;text-transform:uppercase;letter-spacing:.12em;margin:0 0 16px}
  .grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(215px,1fr))}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;display:flex;flex-direction:column;box-shadow:var(--shadow)}
  .thumb{position:relative;aspect-ratio:4/5;width:100%;border:0;padding:0;cursor:zoom-in;background:#ddd;overflow:hidden;display:block}
  .thumb img{width:100%;height:100%;object-fit:cover;display:block}
  .nph{position:absolute;left:10px;bottom:10px;background:rgba(0,0,0,.5);color:#fff;font-size:.68rem;padding:3px 9px;border-radius:999px;pointer-events:none}
  .body{padding:13px 14px 15px;display:flex;flex-direction:column;gap:8px;flex:1}
  .eyebrow{font-size:.66rem;letter-spacing:.16em;text-transform:uppercase;color:var(--gold);font-weight:600}
  .name{font-family:Georgia,serif;font-size:1.02rem;line-height:1.3;margin:0}
  .price{font-size:.98rem;font-variant-numeric:tabular-nums}
  .price .from{color:var(--muted);font-size:.78rem;margin-right:4px}
  .sw{display:flex;gap:6px;flex-wrap:wrap}
  .swatch{width:18px;height:18px;border-radius:999px;border:1px solid rgba(0,0,0,.25);box-shadow:inset 0 0 0 2px var(--surface);cursor:pointer}
  .swatch[aria-pressed="true"]{outline:2px solid var(--gold);outline-offset:1px}
  .spacer{flex:1}
  .wa{display:inline-flex;align-items:center;justify-content:center;gap:8px;background:var(--wa);color:var(--wa-ink);text-decoration:none;font-weight:600;font-size:.9rem;padding:11px 12px;border-radius:10px;border:0;cursor:pointer;width:100%}
  .wa svg{width:17px;height:17px;flex:0 0 auto}
  .lb{position:fixed;inset:0;z-index:60;display:none;place-items:center;padding:18px;background:rgba(15,14,11,.72);backdrop-filter:blur(3px)}
  .lb[open]{display:grid}
  .lb-card{background:var(--surface);border:1px solid var(--line);border-radius:16px;max-width:520px;width:100%;overflow:hidden;box-shadow:var(--shadow);max-height:94vh;display:flex;flex-direction:column}
  .lb-img{position:relative;aspect-ratio:1/1;background:#ccc;flex:0 0 auto}
  .lb-img img{width:100%;height:100%;object-fit:cover;display:block}
  .nav{position:absolute;top:50%;transform:translateY(-50%);width:36px;height:36px;border-radius:999px;border:0;background:rgba(0,0,0,.45);color:#fff;font-size:1.15rem;cursor:pointer;display:grid;place-items:center}
  .nav.prev{left:10px}.nav.next{right:10px}
  .close{position:absolute;top:10px;right:10px;z-index:2;width:34px;height:34px;border-radius:999px;border:0;background:rgba(0,0,0,.45);color:#fff;font-size:1.1rem;cursor:pointer}
  .lb-thumbs{display:flex;gap:6px;padding:10px 12px 0;overflow-x:auto}
  .lb-thumbs img{width:50px;height:50px;object-fit:cover;border-radius:8px;opacity:.55;cursor:pointer;border:2px solid transparent;flex:0 0 auto}
  .lb-thumbs img[data-on]{opacity:1;border-color:var(--gold)}
  .lb-body{padding:16px 20px 20px;overflow:auto}
  .lb-body h3{font-family:Georgia,serif;margin:.1rem 0;font-size:1.3rem}
  .lb-price{color:var(--gold);font-weight:600;margin:2px 0 12px;font-variant-numeric:tabular-nums}
  .optrow{margin:0 0 12px}
  .optrow .lab{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
  .optrow .lab b{color:var(--ink);text-transform:none;letter-spacing:0;font-weight:600;margin-left:4px}
  .bigsw{display:flex;gap:8px;flex-wrap:wrap}
  .bigsw .swatch{width:26px;height:26px}
  .opts{display:flex;gap:8px;flex-wrap:wrap}
  .opt{border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:8px 13px;border-radius:9px;font-size:.85rem;cursor:pointer}
  .opt[aria-pressed="true"]{border-color:var(--gold);background:color-mix(in srgb,var(--gold) 12%,var(--surface))}
  .opt[disabled]{opacity:.35;cursor:not-allowed;text-decoration:line-through}
  .lb-details{white-space:pre-line;color:var(--muted);font-size:.9rem;margin:6px 0 16px;border-top:1px solid var(--line);padding-top:12px}
  footer{border-top:1px solid var(--line);padding:26px 20px 40px;text-align:center;color:var(--muted);font-size:.85rem}
  footer .brand-sm{font-family:Georgia,serif;color:var(--ink);font-size:1.1rem}
</style>

<header class="site">
  <h1 class="brand">__BRAND__</h1><div class="rule"></div>
  <p class="tag">Tap a piece to choose colour &amp; size and enquire — we reply on WhatsApp.</p>
  <div style="text-align:center;margin:14px 0 0;font-size:.82rem;color:var(--muted)">
    Prices in <select id="curSel" aria-label="Currency" style="font:inherit;padding:5px 9px;border-radius:8px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer"></select>
    <span style="opacity:.8">· set to your country, converted from USD (approx.)</span></div>
</header>
<nav class="filters" aria-label="Filter by category"><div class="wrap" id="chips"></div></nav>
<main class="wrap"><p class="count" id="count"></p><div class="grid" id="grid"></div></main>

<div class="lb" id="lb" role="dialog" aria-modal="true" aria-label="Product details">
  <div class="lb-card">
    <div class="lb-img"><button class="close" id="lbClose" aria-label="Close">✕</button>
      <button class="nav prev" id="lbPrev" aria-label="Previous">‹</button>
      <button class="nav next" id="lbNext" aria-label="Next">›</button><div id="lbImg"></div></div>
    <div class="lb-thumbs" id="lbThumbs"></div>
    <div class="lb-body"><div class="eyebrow" id="lbCat"></div><h3 id="lbName"></h3>
      <p class="lb-price" id="lbPrice"></p>
      <div id="lbOpts"></div>
      <p class="lb-details" id="lbDetails"></p>
      <a class="wa" id="lbWa" href="#" target="_blank" rel="noopener"></a></div></div>
</div>
<footer><div class="brand-sm">__BRAND__</div>
  <p>Enquiries &amp; orders via WhatsApp · <a id="footWa" href="#" target="_blank" rel="noopener">Message us</a></p></footer>

<script>
var WHATSAPP="__WHATSAPP__", BRAND="__BRAND__", PRODUCTS=__PRODUCTS__;
var WA='<svg viewBox="0 0 32 32" fill="currentColor"><path d="M16 3C9 3 3.5 8.5 3.5 15.5c0 2.4.7 4.6 1.9 6.6L3 29l7.1-2.3c1.9 1 4 1.6 6.3 1.6h.1c6.9 0 12.5-5.6 12.5-12.5S23 3 16 3zm0 22.7c-2 0-3.9-.5-5.5-1.5l-.4-.2-4.2 1.4 1.4-4.1-.3-.4a10 10 0 01-1.6-5.4C5.4 9.9 10.2 5.3 16 5.3s10.6 4.6 10.6 10.2S21.8 25.7 16 25.7zm5.8-7.6c-.3-.2-1.9-.9-2.2-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a8.2 8.2 0 01-2.4-1.5 9 9 0 01-1.7-2.1c-.2-.3 0-.5.1-.7l.5-.6.3-.5c0-.2 0-.4 0-.6l-1-2.3c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.4-1.2 1.2-1.2 2.9s1.2 3.4 1.4 3.6c.2.2 2.5 3.8 6 5.3.8.4 1.5.6 2 .7.8.3 1.6.2 2.2.1.7-.1 1.9-.8 2.2-1.5.3-.8.3-1.4.2-1.5s-.3-.2-.6-.4z"/></svg>';
function esc(s){return (s||"").replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}

/* currency */
var FALLBACK={USD:1,PHP:58.5,INR:83.3,EUR:.92,GBP:.79,AED:3.67,CAD:1.37,AUD:1.53,SGD:1.35,MYR:4.7,JPY:157,SAR:3.75,NZD:1.66,ZAR:18.5,THB:36,IDR:16200,HKD:7.8,CNY:7.2,KRW:1370,BRL:5.4,MXN:18,CHF:.89,SEK:10.6,PLN:4,QAR:3.64,LKR:300,PKR:278,BDT:118,NGN:1600};
var CC={US:"USD",PH:"PHP",IN:"INR",GB:"GBP",AE:"AED",CA:"CAD",AU:"AUD",NZ:"NZD",SG:"SGD",MY:"MYR",JP:"JPY",SA:"SAR",ZA:"ZAR",TH:"THB",ID:"IDR",HK:"HKD",CN:"CNY",KR:"KRW",BR:"BRL",MX:"MXN",CH:"CHF",SE:"SEK",PL:"PLN",QA:"QAR",LK:"LKR",PK:"PKR",BD:"BDT",NG:"NGN",DE:"EUR",FR:"EUR",ES:"EUR",IT:"EUR",NL:"EUR",IE:"EUR",AT:"EUR",BE:"EUR",PT:"EUR",FI:"EUR",GR:"EUR"};
var MENU=["USD","PHP","INR","GBP","EUR","AED","CAD","AUD","SGD","MYR","JPY","SAR"];
var RATES=null, cur=localStorage.getItem("cur")||"USD";
function rate(){return (RATES&&RATES[cur])||FALLBACK[cur]||1;}
function money(u){if(u==null)return "Enquire";var v=u*rate();try{return new Intl.NumberFormat(undefined,{style:"currency",currency:cur,maximumFractionDigits:v>=100?0:2}).format(v);}catch(e){return cur+" "+(v>=100?Math.round(v):v.toFixed(2));}}
function loadRates(cb){var c=null;try{c=JSON.parse(localStorage.getItem("rates")||"null");}catch(e){}if(c&&c.r&&Date.now()-c.t<864e5){RATES=c.r;cb();return;}fetch("https://open.er-api.com/v6/latest/USD").then(function(r){return r.json();}).then(function(d){if(d&&d.rates){RATES=d.rates;try{localStorage.setItem("rates",JSON.stringify({t:Date.now(),r:RATES}));}catch(e){}}cb();}).catch(cb);}
function detect(){if(localStorage.getItem("cur"))return;fetch("https://api.country.is/").then(function(r){return r.json();}).then(function(d){var c=CC[d&&d.country];if(c){cur=c;syncSel();render();}}).catch(function(){});}
function syncSel(){var s=document.getElementById("curSel");if(s)s.value=cur;}

/* variant helpers */
function minUsd(p){var m=null;p.variants.forEach(function(v){if(v.usd!=null&&(m==null||v.usd<m))m=v.usd;});return m;}
function variesInPrice(p){var s={};p.variants.forEach(function(v){if(v.usd!=null)s[v.usd]=1;});return Object.keys(s).length>1;}
function firstVar(p){return p.variants[0];}
function matchVar(p,sel){
  var best=null,bestScore=-1;
  p.variants.forEach(function(v){
    var sc=0,ok=true;
    for(var k in sel){ if(v.sel[k]===sel[k])sc++; else if(v.sel.hasOwnProperty(k))ok=false; }
    if(ok&&sc>bestScore){bestScore=sc;best=v;}
  });
  return best||p.variants[0];
}
function colorOpt(p){for(var i=0;i<(p.options||[]).length;i++)if(p.options[i].type==="swatch")return p.options[i];return null;}
function cardThumb(p){var v=firstVar(p);return v&&v.thumb?'<img loading="lazy" src="'+v.thumb+'" alt="'+esc(p.name)+'">':'';}

var grid=document.getElementById("grid"), active="All";
var cats=["All"].concat(PRODUCTS.map(function(p){return p.cat;}).filter(function(v,i,a){return a.indexOf(v)===i;}));
function render(){
  var items=PRODUCTS.filter(function(p){return active==="All"||p.cat===active;});
  document.getElementById("count").textContent=items.length+" design"+(items.length===1?"":"s");
  grid.innerHTML=items.map(function(p){
    var i=PRODUCTS.indexOf(p), m=minUsd(p), multi=variesInPrice(p);
    var co=colorOpt(p), sw="";
    if(co&&co.values.length>1) sw='<div class="sw">'+co.values.slice(0,6).map(function(x){return '<span class="swatch" title="'+esc(x.label)+'" style="background:'+(x.hex||"#ccc")+'"></span>';}).join("")+'</div>';
    var np=p.variants.reduce(function(a,v){return Math.max(a,(v.imgs||[]).length);},0);
    return '<article class="card"><button class="thumb" data-i="'+i+'" aria-label="View '+esc(p.name)+'">'+cardThumb(p)+(np>1?'<span class="nph">'+np+' photos</span>':'')+'</button>'+
      '<div class="body"><div class="eyebrow">'+esc(p.cat)+'</div><h3 class="name">'+esc(p.name)+'</h3>'+
      '<div class="price">'+(multi?'<span class="from">from</span>':'')+esc(money(m))+'</div>'+sw+
      '<div class="spacer"></div><a class="wa" data-i="'+i+'" href="#" role="button">'+WA+'Enquire on WhatsApp</a></div></article>';
  }).join("");
}
var chips=document.getElementById("chips");
chips.innerHTML=cats.map(function(c){return '<button class="chip" aria-pressed="'+(c==="All")+'" data-cat="'+esc(c)+'">'+esc(c)+'</button>';}).join("");
chips.addEventListener("click",function(e){var b=e.target.closest(".chip");if(!b)return;active=b.dataset.cat;[].forEach.call(chips.children,function(c){c.setAttribute("aria-pressed",c===b);});render();});

/* lightbox with variant selection */
var lb=document.getElementById("lb"), lbP=null, lbSel={}, lbImgs=[], lbCur=0;
function waLink(p,v){
  var parts=[]; for(var k in v.sel) parts.push(k+": "+v.sel[k]);
  var msg="Hello "+BRAND+"! I'm interested in this piece:\n• "+p.name+(parts.length?" ("+parts.join(", ")+")":"")+
    (v.usd!=null?"\n• Price: "+money(v.usd)+(cur!=="USD"?" (approx, ≈ $"+v.usd+")":""):"")+"\n• Ref: "+p.id+"\n\nIs it available?";
  return "https://wa.me/"+WHATSAPP+"?text="+encodeURIComponent(msg);
}
function showImg(i){if(!lbImgs.length)return;var n=lbImgs.length;lbCur=(i%n+n)%n;
  document.getElementById("lbImg").innerHTML='<img src="'+lbImgs[lbCur]+'" alt="">';
  [].forEach.call(document.getElementById("lbThumbs").children,function(t,j){if(j===lbCur)t.setAttribute("data-on","");else t.removeAttribute("data-on");});}
function applyVariant(){
  var v=matchVar(lbP,lbSel);
  lbImgs=v.imgs||[];
  var strip=document.getElementById("lbThumbs"), multi=lbImgs.length>1;
  strip.style.display=multi?"flex":"none";
  strip.innerHTML=multi?lbImgs.map(function(u,j){return '<img src="'+u+'" data-j="'+j+'" alt="">';}).join(""):"";
  document.getElementById("lbPrev").style.display=multi?"grid":"none";
  document.getElementById("lbNext").style.display=multi?"grid":"none";
  showImg(0);
  document.getElementById("lbPrice").textContent=(v.usd!=null?money(v.usd):"Enquire for price");
  var wa=document.getElementById("lbWa");wa.href=waLink(lbP,v);wa.innerHTML=WA+"Enquire about this piece";
}
function hasVariant(p,sel){return p.variants.some(function(v){for(var k in sel)if(v.sel[k]!==sel[k])return false;return true;});}
function buildOpts(){
  var box=document.getElementById("lbOpts");box.innerHTML="";
  (lbP.options||[]).forEach(function(o){
    var row=document.createElement("div");row.className="optrow";
    var lab=document.createElement("div");lab.className="lab";lab.innerHTML=o.name+"<b>"+esc(lbSel[o.name]||"")+"</b>";row.appendChild(lab);
    var wrap=document.createElement("div");wrap.className=(o.type==="swatch"?"bigsw":"opts");
    o.values.forEach(function(x){
      var test={};for(var k in lbSel)test[k]=lbSel[k];test[o.name]=x.label;
      var avail=hasVariant(lbP,test);
      var el;
      if(o.type==="swatch"){el=document.createElement("span");el.className="swatch";el.title=x.label;el.style.background=x.hex||"#ccc";}
      else{el=document.createElement("button");el.className="opt";el.textContent=x.label;}
      el.setAttribute("aria-pressed", lbSel[o.name]===x.label);
      if(!avail&&o.type!=="swatch")el.setAttribute("disabled","");
      el.addEventListener("click",function(){
        lbSel[o.name]=x.label;
        // if combo invalid, relax other non-color options to the variant's values
        if(!hasVariant(lbP,lbSel)){var v=matchVar(lbP,lbSel);lbSel={};for(var k in v.sel)lbSel[k]=v.sel[k];}
        buildOpts();applyVariant();
      });
      wrap.appendChild(el);
    });
    row.appendChild(wrap);box.appendChild(row);
  });
}
function openLb(p){
  lbP=p; lbSel={}; var v0=firstVar(p); for(var k in v0.sel)lbSel[k]=v0.sel[k];
  document.getElementById("lbCat").textContent=p.cat;
  document.getElementById("lbName").textContent=p.name;
  var d=document.getElementById("lbDetails");d.textContent=p.details||"";d.style.display=(p.details||"").trim()?"block":"none";
  buildOpts(); applyVariant(); lb.setAttribute("open","");
}
document.getElementById("lbPrev").addEventListener("click",function(e){e.stopPropagation();showImg(lbCur-1);});
document.getElementById("lbNext").addEventListener("click",function(e){e.stopPropagation();showImg(lbCur+1);});
document.getElementById("lbThumbs").addEventListener("click",function(e){var t=e.target.closest("img[data-j]");if(t)showImg(+t.dataset.j);});
(function(){var x0=null,im=document.getElementById("lbImg");
  im.addEventListener("touchstart",function(e){x0=e.touches[0].clientX;},{passive:true});
  im.addEventListener("touchend",function(e){if(x0==null)return;var dx=e.changedTouches[0].clientX-x0;x0=null;if(Math.abs(dx)>40)showImg(lbCur+(dx<0?1:-1));},{passive:true});})();
document.addEventListener("keydown",function(e){if(!lb.hasAttribute("open"))return;if(e.key==="ArrowRight")showImg(lbCur+1);if(e.key==="ArrowLeft")showImg(lbCur-1);if(e.key==="Escape")lb.removeAttribute("open");});
grid.addEventListener("click",function(e){
  var wa=e.target.closest("a.wa[data-i]");
  if(wa){e.preventDefault();var p=PRODUCTS[+wa.dataset.i];window.open(waLink(p,firstVar(p)),"_blank");return;}
  var t=e.target.closest(".thumb");if(t)openLb(PRODUCTS[+t.dataset.i]);
});
document.getElementById("lbClose").addEventListener("click",function(){lb.removeAttribute("open");});
lb.addEventListener("click",function(e){if(e.target===lb)lb.removeAttribute("open");});
document.getElementById("footWa").href="https://wa.me/"+WHATSAPP+"?text="+encodeURIComponent("Hello "+BRAND+"! I have a question about your jewelry.");
(function(){var s=document.getElementById("curSel");if(s){s.innerHTML=MENU.map(function(c){return '<option>'+c+'</option>';}).join("");s.value=cur;
  s.addEventListener("change",function(){cur=s.value;try{localStorage.setItem("cur",cur);}catch(e){}render();if(lb.hasAttribute("open"))applyVariant();});}
  loadRates(function(){syncSel();render();}); detect();})();
</script>
"""


def build(products, brand, whatsapp):
    return (TEMPLATE.replace("__PRODUCTS__", json.dumps(products, ensure_ascii=False))
            .replace("__WHATSAPP__", re.sub(r"\D", "", whatsapp))
            .replace("__BRAND__", html.escape(brand)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("--out", required=True)
    ap.add_argument("--brand", default="SRX DIAMONDS")
    ap.add_argument("--whatsapp", default="919723891732")
    a = ap.parse_args()
    products = json.load(open(a.data, encoding="utf-8"))
    Path(a.out).write_text(build(products, a.brand, a.whatsapp), encoding="utf-8")
    print(f"built {a.out}: {len(products)} designs")


if __name__ == "__main__":
    main()
