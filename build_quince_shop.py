#!/usr/bin/env python3
r"""Build a Quince-style jewelry storefront from a variants JSON.

Replicates the quince.com/shop/jewelry experience: promo bar, serif header,
circular category nav, a Color / Size / Material / Price Range filter bar with
a sort control, a responsive product grid (rating + colour-swatch photo swap),
and a product-detail modal where changing colour or carat swaps the gallery and
price. Enquiries go to WhatsApp; prices auto-convert to the visitor's currency.
"""
import argparse, html, json, re
from pathlib import Path

TEMPLATE = r"""<title>__BRAND__ — Fine Jewelry</title>
<style>
  :root{
    --bg:#fff;--ink:#171512;--muted:#767066;--faint:#a49d90;--line:#e8e4dc;--panel:#f3f1ec;
    --promo:#3c2b1e;--promo-ink:#f4ece0;--cta:#ef9d6b;--cta-ink:#2a1a0e;--cta-h:#e88b53;
    --star:#141312;--wish:#c26b6b;--maxw:1360px;--serif:"Times New Roman",Georgia,serif;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }
  *{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.45;-webkit-font-smoothing:antialiased}
  a{color:inherit;text-decoration:none}
  .promo{background:var(--promo);color:var(--promo-ink);text-align:center;font-size:.8rem;letter-spacing:.02em;padding:8px 12px}
  header.site{position:sticky;top:0;z-index:40;background:var(--bg);border-bottom:1px solid var(--line)}
  .hrow{max-width:var(--maxw);margin:0 auto;display:flex;align-items:center;gap:20px;padding:16px 22px}
  .logo{font-family:var(--serif);font-size:1.7rem;letter-spacing:.01em;font-weight:500;white-space:nowrap}
  .search{flex:1;max-width:460px;margin:0 auto;position:relative}
  .search input{width:100%;border:1px solid var(--line);background:#fbfaf8;border-radius:4px;padding:10px 14px;font:inherit;font-size:.9rem;color:var(--ink)}
  .search input:focus{outline:none;border-color:var(--faint)}
  .icons{display:flex;align-items:center;gap:18px;color:var(--ink)}
  .icons button{background:none;border:0;cursor:pointer;color:inherit;display:flex;align-items:center;gap:6px;font:inherit;font-size:.85rem;padding:0}
  .icons svg{width:20px;height:20px}
  nav.main{border-top:1px solid var(--line)}
  nav.main .wrap{max-width:var(--maxw);margin:0 auto;display:flex;gap:26px;padding:11px 22px;overflow-x:auto;scrollbar-width:none;font-size:.86rem}
  nav.main .wrap::-webkit-scrollbar{display:none}
  nav.main a{white-space:nowrap;color:var(--ink);cursor:pointer;padding:2px 0;border-bottom:2px solid transparent}
  nav.main a.on,nav.main a:hover{border-color:var(--ink)}
  .container{max-width:var(--maxw);margin:0 auto;padding:0 22px}
  h1.page{font-family:var(--serif);font-weight:500;font-size:1.55rem;margin:26px 0 16px}
  .cats{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:8px;margin-bottom:6px}
  .cats::-webkit-scrollbar{display:none}
  .catbtn{flex:0 0 auto;width:112px;background:none;border:0;cursor:pointer;text-align:center;color:var(--ink)}
  .catbtn .disc{width:92px;height:92px;border-radius:50%;margin:0 auto 8px;background:var(--panel);overflow:hidden;border:1px solid var(--line);display:grid;place-items:center}
  .catbtn .disc img{width:100%;height:100%;object-fit:cover}
  .catbtn.on .disc{outline:1.5px solid var(--ink);outline-offset:2px}
  .catbtn span{font-size:.8rem;color:var(--muted)}
  .catbtn.on span{color:var(--ink)}
  .toolbar{position:sticky;top:63px;z-index:30;background:var(--bg);display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}
  .fbtn{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);background:#fbfaf8;border-radius:999px;padding:8px 15px;font:inherit;font-size:.83rem;cursor:pointer;color:var(--ink);white-space:nowrap}
  .fbtn .car{font-size:.6rem;opacity:.7}
  .fbtn.act{border-color:var(--ink)}
  .fbtn .badge{background:var(--ink);color:#fff;border-radius:999px;font-size:.68rem;padding:1px 6px;margin-left:2px}
  .spacer{flex:1}
  .count{color:var(--muted);font-size:.82rem;white-space:nowrap}
  .sortwrap{position:relative}
  select.sort{appearance:none;border:1px solid var(--line);background:#fbfaf8;border-radius:999px;padding:8px 30px 8px 15px;font:inherit;font-size:.83rem;cursor:pointer;color:var(--ink)}
  .sortwrap::after{content:"⌄";position:absolute;right:13px;top:47%;transform:translateY(-50%);pointer-events:none;color:var(--muted)}
  /* filter popovers */
  .pop{position:absolute;z-index:35;margin-top:8px;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 34px -14px rgba(0,0,0,.28);padding:14px;min-width:230px;max-height:60vh;overflow:auto;display:none}
  .pop.open{display:block}
  .pop h4{margin:0 0 10px;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
  .opts{display:flex;flex-direction:column;gap:2px}
  .opt{display:flex;align-items:center;gap:9px;padding:6px 4px;font-size:.88rem;cursor:pointer;border-radius:6px}
  .opt:hover{background:var(--panel)}
  .opt input{accent-color:var(--ink);width:16px;height:16px}
  .opt .sw{width:16px;height:16px;border-radius:50%;border:1px solid rgba(0,0,0,.22)}
  .sizewrap{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
  .sizecell{border:1px solid var(--line);border-radius:6px;text-align:center;padding:8px 2px;font-size:.8rem;cursor:pointer}
  .sizecell.on{border-color:var(--ink);background:var(--panel)}
  .popfoot{display:flex;justify-content:space-between;align-items:center;margin-top:12px;gap:10px}
  .lnk{background:none;border:0;color:var(--muted);text-decoration:underline;cursor:pointer;font:inherit;font-size:.8rem}
  .applybtn{background:var(--ink);color:#fff;border:0;border-radius:999px;padding:8px 18px;font:inherit;font-size:.82rem;cursor:pointer}
  .chips{display:flex;flex-wrap:wrap;gap:8px;padding:12px 0 0}
  .chip{display:inline-flex;align-items:center;gap:6px;background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:5px 10px;font-size:.78rem;color:var(--ink)}
  .chip button{background:none;border:0;cursor:pointer;color:var(--muted);font-size:.9rem;line-height:1;padding:0}
  /* grid */
  .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:26px 22px;padding:22px 0 60px}
  .card{cursor:pointer;display:flex;flex-direction:column}
  .ph{position:relative;background:var(--panel);aspect-ratio:1/1;overflow:hidden;border-radius:3px}
  .ph img{width:100%;height:100%;object-fit:cover;display:block;transition:opacity .18s}
  .wish{position:absolute;top:10px;right:10px;width:30px;height:30px;border-radius:50%;background:rgba(255,255,255,.82);border:0;cursor:pointer;display:grid;place-items:center;color:var(--ink)}
  .wish svg{width:16px;height:16px}.wish.on{color:var(--wish)}
  .tag{position:absolute;left:10px;top:10px;background:#fff;color:var(--ink);font-size:.66rem;letter-spacing:.03em;padding:3px 8px;border-radius:3px;border:1px solid var(--line)}
  .meta{padding:11px 2px 0}
  .metal{font-size:.76rem;color:var(--muted);margin-bottom:3px}
  .nr{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
  .nm{font-size:.9rem;line-height:1.3}
  .pr{font-size:.9rem;white-space:nowrap;font-variant-numeric:tabular-nums}
  .pr .from{color:var(--muted);font-size:.72rem;margin-right:3px}
  .pr .was{color:var(--faint);text-decoration:line-through;font-size:.78rem;margin-right:5px}
  .rate{display:flex;align-items:center;gap:4px;color:var(--muted);font-size:.78rem;margin-top:5px}
  .rate svg{width:12px;height:12px;color:var(--star)}
  .sw6{display:flex;gap:6px;margin-top:8px}
  .sw6 .s{width:15px;height:15px;border-radius:50%;border:1px solid rgba(0,0,0,.22);cursor:pointer}
  .sw6 .s.on{outline:1.4px solid var(--ink);outline-offset:1.5px}
  .empty{padding:60px 0;text-align:center;color:var(--muted)}
  /* PDP modal */
  .lb{position:fixed;inset:0;z-index:60;display:none;background:rgba(28,24,18,.55);backdrop-filter:blur(2px)}
  .lb.open{display:block}
  .lb-scroll{position:absolute;inset:0;overflow:auto;display:flex;align-items:flex-start;justify-content:center;padding:30px 16px}
  .pdp{background:#fff;border-radius:12px;max-width:1000px;width:100%;display:grid;grid-template-columns:1.05fr 1fr;overflow:hidden;box-shadow:0 30px 80px -30px rgba(0,0,0,.5)}
  .pclose{position:absolute;top:18px;right:18px;width:38px;height:38px;border-radius:50%;background:#fff;border:1px solid var(--line);cursor:pointer;font-size:1.1rem;z-index:3}
  .gal{background:var(--panel);padding:16px;display:flex;flex-direction:column;gap:12px}
  .gmain{position:relative;background:#fff;border-radius:6px;aspect-ratio:1/1;overflow:hidden}
  .gmain img{width:100%;height:100%;object-fit:cover;display:block}
  .gnav{position:absolute;top:50%;transform:translateY(-50%);width:34px;height:34px;border-radius:50%;border:0;background:rgba(255,255,255,.85);cursor:pointer;font-size:1.05rem}
  .gnav.p{left:10px}.gnav.n{right:10px}
  .gthumbs{display:flex;gap:8px;flex-wrap:wrap}
  .gthumbs img{width:56px;height:56px;object-fit:cover;border-radius:5px;border:1.5px solid transparent;cursor:pointer;opacity:.6}
  .gthumbs img.on{opacity:1;border-color:var(--ink)}
  .info{padding:30px 32px 34px;overflow:auto}
  .info .eb{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
  .info h2{font-family:var(--serif);font-weight:500;font-size:1.5rem;margin:6px 0 8px;line-height:1.2}
  .info .rate{margin:0 0 12px}
  .price{font-size:1.15rem;margin:0 0 18px;font-variant-numeric:tabular-nums}
  .price .was{color:var(--faint);text-decoration:line-through;font-size:.95rem;margin-right:8px}
  .price .save{color:#3f7d4f;font-size:.82rem;margin-left:8px}
  .orow{margin:0 0 16px}
  .orow .l{font-size:.74rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
  .orow .l b{color:var(--ink);text-transform:none;letter-spacing:0;font-weight:600;margin-left:5px}
  .bsw{display:flex;gap:9px;flex-wrap:wrap}
  .bsw .s{width:30px;height:30px;border-radius:50%;border:1px solid rgba(0,0,0,.25);cursor:pointer}
  .bsw .s.on{outline:2px solid var(--ink);outline-offset:2px}
  .pills{display:flex;gap:8px;flex-wrap:wrap}
  .pill{border:1px solid var(--line);background:#fff;border-radius:7px;padding:9px 15px;font:inherit;font-size:.86rem;cursor:pointer;color:var(--ink)}
  .pill.on{border-color:var(--ink);background:var(--panel)}
  .pill[disabled]{opacity:.32;cursor:not-allowed;text-decoration:line-through}
  .cta{display:flex;align-items:center;justify-content:center;gap:9px;width:100%;background:var(--cta);color:var(--cta-ink);border:0;border-radius:999px;padding:15px;font:inherit;font-weight:600;font-size:.98rem;cursor:pointer;margin:22px 0 8px}
  .cta:hover{background:var(--cta-h)}
  .cta svg{width:19px;height:19px}
  .ship{font-size:.78rem;color:var(--muted);text-align:center;margin-bottom:10px}
  .acc{border-top:1px solid var(--line);margin-top:14px}
  .acc button{width:100%;background:none;border:0;display:flex;justify-content:space-between;align-items:center;padding:15px 2px;font:inherit;font-size:.82rem;letter-spacing:.1em;text-transform:uppercase;cursor:pointer;color:var(--ink)}
  .acc .body{font-size:.88rem;color:var(--muted);white-space:pre-line;padding:0 2px 16px;display:none}
  .acc.open .body{display:block}
  footer{background:#1d1a15;color:#d9d3c7;margin-top:20px;padding:40px 22px}
  footer .w{max-width:var(--maxw);margin:0 auto;display:flex;flex-wrap:wrap;gap:30px;justify-content:space-between}
  footer .logo{color:#fff;font-size:1.4rem}
  footer a{color:#d9d3c7;font-size:.85rem;display:block;margin:6px 0}
  footer .muted{color:#8b8478;font-size:.78rem;margin-top:16px}
  @media(max-width:900px){.pdp{grid-template-columns:1fr}.info{padding:22px}}
  @media(max-width:720px){
    .grid{grid-template-columns:repeat(2,1fr);gap:22px 14px}
    .hrow{gap:12px;padding:12px 16px}.search{order:3;flex-basis:100%;max-width:none;margin:8px 0 0}
    .logo{font-size:1.35rem}.container{padding:0 16px}.toolbar{top:55px}
    .catbtn{width:88px}.catbtn .disc{width:72px;height:72px}
  }
</style>

<div class="promo">Complimentary shipping &amp; 365-day returns · Lab-grown diamonds at honest prices</div>
<header class="site">
  <div class="hrow">
    <div class="logo">__BRAND__</div>
    <div class="search"><input id="q" type="search" placeholder="Search jewelry" aria-label="Search"></div>
    <div class="icons">
      <button id="curBtn" title="Currency"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 2.5 15.4 0 18M12 3c-2.5 2.6-2.5 15.4 0 18"/></svg><span id="curLbl">USD</span></button>
      <button title="Wishlist"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 21s-7-4.5-9.5-9C1 9 2.5 5.5 6 5.5c2 0 3.2 1.2 4 2.3.8-1.1 2-2.3 4-2.3 3.5 0 5 3.5 3.5 6.5C19 16.5 12 21 12 21z"/></svg></button>
      <button id="waTop" title="WhatsApp"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 00-8.6 15l-1.3 4.7L6.9 20.4A10 10 0 1012 2zm0 2a8 8 0 11-4.2 14.8l-.3-.2-2.5.7.7-2.4-.2-.3A8 8 0 0112 4z"/></svg></button>
    </div>
  </div>
  <nav class="main"><div class="wrap" id="topnav"></div></nav>
</header>

<div class="container">
  <h1 class="page">All Jewelry</h1>
  <div class="cats" id="cats"></div>
  <div class="toolbar">
    <button class="fbtn" id="fFilter"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M6 12h12M10 18h4"/></svg> Filter</button>
    <button class="fbtn" data-pop="colors">Color <span class="car">▾</span></button>
    <button class="fbtn" data-pop="sizes">Size <span class="car">▾</span></button>
    <button class="fbtn" data-pop="materials">Material <span class="car">▾</span></button>
    <button class="fbtn" data-pop="prices">Price Range <span class="car">▾</span></button>
    <span class="spacer"></span>
    <span class="count" id="count"></span>
    <div class="sortwrap"><select class="sort" id="sort">
      <option value="featured">Sort By: Featured</option>
      <option value="plow">Price: Low to High</option>
      <option value="phigh">Price: High to Low</option>
      <option value="rating">Top Rated</option>
    </select></div>
  </div>
  <div id="chips" class="chips"></div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">No pieces match these filters. <button class="lnk" id="clearAll">Clear all</button></div>
</div>

<div class="lb" id="lb"><div class="lb-scroll"><div class="pdp" id="pdp">
  <button class="pclose" id="pclose" aria-label="Close">✕</button>
  <div class="gal">
    <div class="gmain"><button class="gnav p" id="gp">‹</button><div id="gimg"></div><button class="gnav n" id="gn">›</button></div>
    <div class="gthumbs" id="gthumbs"></div>
  </div>
  <div class="info">
    <div class="eb" id="pcat"></div><h2 id="pname"></h2>
    <div class="rate" id="prate"></div>
    <p class="price" id="pprice"></p>
    <div id="popts"></div>
    <button class="cta" id="pcta"></button>
    <div class="ship">Enquire on WhatsApp — we reply fast with availability &amp; details.</div>
    <div class="acc" id="pacc"><button id="paccBtn">Details <span>+</span></button><div class="body" id="pdetails"></div></div>
  </div>
</div></div></div>

<footer><div class="w">
  <div><div class="logo">__BRAND__</div><div class="muted">Fine lab-grown diamond jewelry.<br>Enquiries &amp; orders on WhatsApp.</div></div>
  <div><a id="fwa" target="_blank" rel="noopener">Message us on WhatsApp</a><a>Necklaces</a><a>Bracelets</a><a>Rings</a><a>Earrings</a></div>
</div></footer>

<div class="pop" id="popPanel"></div>

<script>
var WHATSAPP="__WHATSAPP__", BRAND="__BRAND__", PRODUCTS=__PRODUCTS__;
var WA='<svg viewBox="0 0 32 32" fill="currentColor"><path d="M16 3C9 3 3.5 8.5 3.5 15.5c0 2.4.7 4.6 1.9 6.6L3 29l7.1-2.3c1.9 1 4 1.6 6.3 1.6h.1c6.9 0 12.5-5.6 12.5-12.5S23 3 16 3zm0 22.7c-2 0-3.9-.5-5.5-1.5l-.4-.2-4.2 1.4 1.4-4.1-.3-.4a10 10 0 01-1.6-5.4C5.4 9.9 10.2 5.3 16 5.3s10.6 4.6 10.6 10.2S21.8 25.7 16 25.7zm5.8-7.6c-.3-.2-1.9-.9-2.2-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a8.2 8.2 0 01-2.4-1.5 9 9 0 01-1.7-2.1c-.2-.3 0-.5.1-.7l.5-.6.3-.5c0-.2 0-.4 0-.6l-1-2.3c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.4-1.2 1.2-1.2 2.9s1.2 3.4 1.4 3.6c.2.2 2.5 3.8 6 5.3.8.4 1.5.6 2 .7.8.3 1.6.2 2.2.1.7-.1 1.9-.8 2.2-1.5.3-.8.3-1.4.2-1.5s-.3-.2-.6-.4z"/></svg>';
var STAR='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.9 21l1.2-6.8-5-4.9 6.9-1z"/></svg>';
function esc(s){return (s||"").replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}

/* ---------- currency ---------- */
var FALLBACK={USD:1,PHP:58.5,INR:83.3,EUR:.92,GBP:.79,AED:3.67,CAD:1.37,AUD:1.53,SGD:1.35,MYR:4.7,JPY:157,SAR:3.75,NZD:1.66,ZAR:18.5,THB:36,IDR:16200,HKD:7.8,CNY:7.2,KRW:1370,BRL:5.4,MXN:18,CHF:.89,SEK:10.6,PLN:4,QAR:3.64,LKR:300,PKR:278,BDT:118,NGN:1600};
var CC={US:"USD",PH:"PHP",IN:"INR",GB:"GBP",AE:"AED",CA:"CAD",AU:"AUD",NZ:"NZD",SG:"SGD",MY:"MYR",JP:"JPY",SA:"SAR",ZA:"ZAR",TH:"THB",ID:"IDR",HK:"HKD",CN:"CNY",KR:"KRW",BR:"BRL",MX:"MXN",CH:"CHF",SE:"SEK",PL:"PLN",QA:"QAR",LK:"LKR",PK:"PKR",BD:"BDT",NG:"NGN",DE:"EUR",FR:"EUR",ES:"EUR",IT:"EUR",NL:"EUR",IE:"EUR",AT:"EUR",BE:"EUR",PT:"EUR",FI:"EUR",GR:"EUR"};
var MENU=["USD","PHP","INR","GBP","EUR","AED","CAD","AUD","SGD","MYR","JPY","SAR"];
var RATES=null, cur=localStorage.getItem("cur")||"USD";
function rate(){return (RATES&&RATES[cur])||FALLBACK[cur]||1;}
function money(u){if(u==null)return "Enquire";var v=u*rate();try{return new Intl.NumberFormat(undefined,{style:"currency",currency:cur,maximumFractionDigits:v>=100?0:2}).format(v);}catch(e){return cur+" "+(v>=100?Math.round(v):v.toFixed(2));}}
function loadRates(cb){var c=null;try{c=JSON.parse(localStorage.getItem("rates")||"null");}catch(e){}if(c&&c.r&&Date.now()-c.t<864e5){RATES=c.r;cb();return;}fetch("https://open.er-api.com/v6/latest/USD").then(function(r){return r.json();}).then(function(d){if(d&&d.rates){RATES=d.rates;try{localStorage.setItem("rates",JSON.stringify({t:Date.now(),r:RATES}));}catch(e){}}cb();}).catch(cb);}
function detect(){if(localStorage.getItem("cur"))return;fetch("https://api.country.is/").then(function(r){return r.json();}).then(function(d){var c=CC[d&&d.country];if(c){cur=c;document.getElementById("curLbl").textContent=cur;render();}}).catch(function(){});}
function cycleCur(){var i=MENU.indexOf(cur);cur=MENU[(i+1)%MENU.length];try{localStorage.setItem("cur",cur);}catch(e){}document.getElementById("curLbl").textContent=cur;render();if(lb.classList.contains("open"))applyVariant();}

/* ---------- variant helpers ---------- */
function firstVar(p){return p.variants[0];}
function minUsd(p){var m=null;p.variants.forEach(function(v){if(v.usd!=null&&(m==null||v.usd<m))m=v.usd;});return m;}
function variesInPrice(p){var s={};p.variants.forEach(function(v){if(v.usd!=null)s[v.usd]=1;});return Object.keys(s).length>1;}
function colorOpt(p){for(var i=0;i<(p.options||[]).length;i++)if(p.options[i].type==="swatch")return p.options[i];return null;}
function optIsFree(p,name){return !p.variants.some(function(v){return v.sel.hasOwnProperty(name);});}
function boundSel(p,sel){var o={};for(var k in sel){if(sel[k]&&!optIsFree(p,k))o[k]=sel[k];}return o;}
function hasVariant(p,sel){return p.variants.some(function(v){for(var k in sel)if(v.sel[k]!==sel[k])return false;return true;});}
function matchVar(p,sel){var best=null,bs=-1;p.variants.forEach(function(v){var sc=0,ok=true;for(var k in sel){if(v.sel[k]===sel[k])sc++;else if(v.sel.hasOwnProperty(k))ok=false;}if(ok&&sc>bs){bs=sc;best=v;}});return best||p.variants[0];}
function metalOf(v){return (v.sel&&v.sel.Color)||"";}

/* ---------- filter config (Quince) ---------- */
var QCOLORS=[["Yellow","#ecb91f"],["Grey","#e5e5e7"],["White","#ffffff"],["Pink","#faf0f7"],["Red","#c52e35"],["Blue","#1b4f9b"],["Green","#62664d"],["Brown","#9c673b"],["Tan","#bbb09e"]];
var MATERIAL_ORDER=["Lab Grown Diamond","Diamond","14k Gold","Gold Vermeil","Gemstone","Pearl","Platinum","Sterling Silver","Tungsten Carbide","10k Gold"];
var PRICE_BUCKETS=[["$25-50",25,50],["$50-75",50,75],["$75-100",75,100],["$100-200",100,200],["$200-300",200,300],["$300-400",300,400],["$400-500",400,500],["$500-600",500,600],["$600-1000",600,1000],["$1000-2000",1000,2000],["$2000-3000",2000,3000],["> $3000",3000,1e12]];
var SIZE_ORDER=["4","4.5","5","5.5","6","6.5","7","7.5","8","8.5","9","9.5","10","10.5","11","11.5","12","12.5","13","13.5","14","12mm","15mm","18mm","25mm","35mm","45mm","6\"","6.5\"","7\"","7.5\"","8\"","16\"","18\"","20\"","22\"","24\"","6.75\"","14-16\"","16-18\"","18-20\"","Small","Medium","Large","One Size"];
function sizeRank(s){var i=SIZE_ORDER.indexOf(s);return i<0?999:i;}

function pColors(p){var c=colorOpt(p);var out={};if(c)c.values.forEach(function(v){if(v.q)out[v.q]=1;});return Object.keys(out);}
function pSizes(p){for(var i=0;i<(p.options||[]).length;i++)if(p.options[i].name==="Size")return p.options[i].values.map(function(v){return v.label;});return [];}
function pMaterials(p){return p.materials||["Lab Grown Diamond"];}
function pBucket(p){var u=minUsd(p);for(var i=0;i<PRICE_BUCKETS.length;i++){var b=PRICE_BUCKETS[i];if(u>=b[1]&&u<b[2])return b[0];}return null;}

/* available facet values present in catalog */
function present(fn){var s={};PRODUCTS.forEach(function(p){(Array.isArray(fn(p))?fn(p):[fn(p)]).forEach(function(x){if(x)s[x]=(s[x]||0)+1;});});return s;}
var HAS_COLOR=present(pColors), HAS_SIZE=present(pSizes), HAS_MAT=present(pMaterials), HAS_PRICE=present(function(p){return pBucket(p);});

/* ---------- state ---------- */
var F={cat:"All",sort:"featured",q:"",colors:{},sizes:{},materials:{},prices:{}};
function anyF(){return Object.keys(F.colors).length||Object.keys(F.sizes).length||Object.keys(F.materials).length||Object.keys(F.prices).length;}
function matches(p){
  if(F.cat!=="All"&&p.cat!==F.cat)return false;
  if(F.q){var t=(p.name+" "+p.cat).toLowerCase();if(t.indexOf(F.q.toLowerCase())<0)return false;}
  var cs=Object.keys(F.colors);if(cs.length){var pc=pColors(p);if(!cs.some(function(c){return pc.indexOf(c)>=0;}))return false;}
  var ss=Object.keys(F.sizes);if(ss.length){var ps=pSizes(p);if(!ss.some(function(s){return ps.indexOf(s)>=0;}))return false;}
  var ms=Object.keys(F.materials);if(ms.length){var pm=pMaterials(p);if(!ms.some(function(m){return pm.indexOf(m)>=0;}))return false;}
  var bs=Object.keys(F.prices);if(bs.length){if(bs.indexOf(pBucket(p))<0)return false;}
  return true;
}
function filtered(){
  var items=PRODUCTS.filter(matches);
  if(F.sort==="plow")items.sort(function(a,b){return (minUsd(a)||0)-(minUsd(b)||0);});
  else if(F.sort==="phigh")items.sort(function(a,b){return (minUsd(b)||0)-(minUsd(a)||0);});
  else if(F.sort==="rating")items.sort(function(a,b){return (b.rating||0)-(a.rating||0);});
  return items;
}

/* ---------- top nav + categories ---------- */
var CATS=[];PRODUCTS.forEach(function(p){if(CATS.indexOf(p.cat)<0)CATS.push(p.cat);});
var CORDER=["Necklaces","Bracelets","Rings","Engagement Rings","Earrings"];
CATS.sort(function(a,b){var i=CORDER.indexOf(a),j=CORDER.indexOf(b);return (i<0?9:i)-(j<0?9:j);});
(function(){
  var nav=document.getElementById("topnav");
  var links=["New Arrivals","Best Sellers"].concat(CATS);
  nav.innerHTML=links.map(function(c){var cat=CATS.indexOf(c)>=0?c:"All";return '<a data-cat="'+esc(cat)+'">'+esc(c)+'</a>';}).join("");
  nav.addEventListener("click",function(e){var a=e.target.closest("a[data-cat]");if(a){setCat(a.dataset.cat);}});
  var cw=document.getElementById("cats");
  var all=[["All","All"]].concat(CATS.map(function(c){return [c,c];}));
  cw.innerHTML=all.map(function(x){
    var img="";if(x[0]!=="All"){var p=PRODUCTS.filter(function(q){return q.cat===x[0];})[0];if(p)img='<img src="'+firstVar(p).thumb+'" alt="">';}
    else{var p0=PRODUCTS[0];if(p0)img='<img src="'+firstVar(p0).thumb+'" alt="">';}
    return '<button class="catbtn" data-cat="'+esc(x[0])+'"><div class="disc">'+img+'</div><span>'+esc(x[1])+'</span></button>';
  }).join("");
  cw.addEventListener("click",function(e){var b=e.target.closest(".catbtn");if(b)setCat(b.dataset.cat);});
})();
function setCat(c){F.cat=c;render();}

/* ---------- grid ---------- */
var grid=document.getElementById("grid");
function cardHTML(p,i){
  var v=firstVar(p),m=minUsd(p),multi=variesInPrice(p),co=colorOpt(p);
  var np=p.variants.reduce(function(a,x){return Math.max(a,(x.imgs||[]).length);},0);
  var sw="";if(co&&co.values.length>1)sw='<div class="sw6">'+co.values.slice(0,6).map(function(x,j){return '<span class="s'+(j===0?" on":"")+'" data-ci="'+j+'" title="'+esc(x.label)+'" style="background:'+(x.hex||"#ccc")+'"></span>';}).join("")+'</div>';
  var was=v.orig?'<span class="was">'+esc(money(v.orig))+'</span>':'';
  var rate=p.rating?'<div class="rate">'+STAR+esc(p.rating.toFixed(1))+(p.reviews?' <span style="color:var(--faint)">('+p.reviews+')</span>':'')+'</div>':'';
  return '<article class="card" data-i="'+i+'">'+
    '<div class="ph"><img src="'+v.thumb+'" alt="'+esc(p.name)+'" data-img>'+
      '<button class="wish" data-wish aria-label="Save">'+
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 21s-7-4.5-9.5-9C1 9 2.5 5.5 6 5.5c2 0 3.2 1.2 4 2.3.8-1.1 2-2.3 4-2.3 3.5 0 5 3.5 3.5 6.5C19 16.5 12 21 12 21z"/></svg></button>'+
      (np>1?'<span class="tag">'+np+' photos</span>':'')+'</div>'+
    '<div class="meta"><div class="metal" data-metal>'+esc(metalOf(v))+'</div>'+
      '<div class="nr"><div class="nm">'+esc(p.name)+'</div><div class="pr">'+(multi?'<span class="from">from</span>':'')+was+esc(money(m))+'</div></div>'+
      rate+sw+'</div></article>';
}
function render(){
  var items=filtered();
  document.getElementById("count").textContent=items.length+" item"+(items.length===1?"":"s");
  grid.innerHTML=items.map(function(p){return cardHTML(p,PRODUCTS.indexOf(p));}).join("");
  document.getElementById("empty").style.display=items.length?"none":"block";
  // sync category + nav active states
  [].forEach.call(document.querySelectorAll(".catbtn"),function(b){b.classList.toggle("on",b.dataset.cat===F.cat);});
  [].forEach.call(document.querySelectorAll("#topnav a"),function(a){a.classList.toggle("on",a.dataset.cat===F.cat&&F.cat!=="All");});
  [].forEach.call(document.querySelectorAll(".fbtn[data-pop]"),function(b){var k=b.dataset.pop;var n=Object.keys(F[k]).length;b.classList.toggle("act",!!n);b.querySelector(".badge")&&b.querySelector(".badge").remove();if(n){var s=document.createElement("span");s.className="badge";s.textContent=n;b.appendChild(s);}});
  renderChips();
}
grid.addEventListener("mouseover",function(e){var s=e.target.closest(".s[data-ci]");if(!s)return;var card=s.closest(".card");var p=PRODUCTS[+card.dataset.i];var co=colorOpt(p);var val=co.values[+s.dataset.ci];var v=matchVar(p,{Color:val.label});card.querySelector("[data-img]").src=v.thumb;card.querySelector("[data-metal]").textContent=val.label;card.querySelectorAll(".s").forEach(function(x){x.classList.toggle("on",x===s);});});
grid.addEventListener("click",function(e){
  var w=e.target.closest("[data-wish]");if(w){e.stopPropagation();w.classList.toggle("on");return;}
  var s=e.target.closest(".s[data-ci]");
  var card=e.target.closest(".card");if(!card)return;var p=PRODUCTS[+card.dataset.i];
  if(s){openPDP(p,+s.dataset.ci);return;}
  openPDP(p,0);
});

/* ---------- chips ---------- */
function renderChips(){
  var box=document.getElementById("chips");var out=[];
  ["colors","sizes","materials","prices"].forEach(function(k){Object.keys(F[k]).forEach(function(v){out.push('<span class="chip">'+esc(v)+'<button data-ck="'+k+'" data-cv="'+esc(v)+'">✕</button></span>');});});
  if(F.q)out.push('<span class="chip">“'+esc(F.q)+'”<button data-clearq>✕</button></span>');
  box.innerHTML=out.join("");
}
document.getElementById("chips").addEventListener("click",function(e){
  var b=e.target.closest("[data-ck]");if(b){delete F[b.dataset.ck][b.dataset.cv];render();buildPop(openPop);return;}
  if(e.target.closest("[data-clearq]")){F.q="";document.getElementById("q").value="";render();}
});

/* ---------- filter popovers ---------- */
var panel=document.getElementById("popPanel"),openPop=null;
function buildPop(kind){
  if(!kind){panel.classList.remove("open");return;}
  var html="",title={colors:"Color",sizes:"Size",materials:"Material",prices:"Price Range"}[kind];
  html+='<h4>'+title+'</h4>';
  if(kind==="colors"){html+='<div class="opts">'+QCOLORS.filter(function(c){return HAS_COLOR[c[0]];}).map(function(c){return '<label class="opt"><input type="checkbox" data-v="'+c[0]+'" '+(F.colors[c[0]]?"checked":"")+'><span class="sw" style="background:'+c[1]+'"></span>'+c[0]+' <span style="color:var(--faint);margin-left:auto">'+HAS_COLOR[c[0]]+'</span></label>';}).join("")+'</div>';}
  else if(kind==="materials"){html+='<div class="opts">'+MATERIAL_ORDER.filter(function(m){return HAS_MAT[m];}).map(function(m){return '<label class="opt"><input type="checkbox" data-v="'+esc(m)+'" '+(F.materials[m]?"checked":"")+'>'+esc(m)+' <span style="color:var(--faint);margin-left:auto">'+HAS_MAT[m]+'</span></label>';}).join("")+'</div>';}
  else if(kind==="prices"){html+='<div class="opts">'+PRICE_BUCKETS.filter(function(b){return HAS_PRICE[b[0]];}).map(function(b){return '<label class="opt"><input type="checkbox" data-v="'+esc(b[0])+'" '+(F.prices[b[0]]?"checked":"")+'>'+esc(b[0])+' <span style="color:var(--faint);margin-left:auto">'+HAS_PRICE[b[0]]+'</span></label>';}).join("")+'</div>';}
  else if(kind==="sizes"){var sz=Object.keys(HAS_SIZE).sort(function(a,b){return sizeRank(a)-sizeRank(b);});html+='<div class="sizewrap">'+sz.map(function(s){return '<div class="sizecell'+(F.sizes[s]?" on":"")+'" data-v="'+esc(s)+'">'+esc(s)+'</div>';}).join("")+'</div>';}
  html+='<div class="popfoot"><button class="lnk" data-clear>Clear</button><button class="applybtn" data-apply>View ('+filtered().length+')</button></div>';
  panel.innerHTML=html;panel.classList.add("open");
}
function placePop(btn){var r=btn.getBoundingClientRect();panel.style.left=Math.max(10,Math.min(r.left,window.innerWidth-panel.offsetWidth-10))+"px";panel.style.top=(r.bottom+window.scrollY)+"px";}
document.querySelectorAll(".fbtn[data-pop]").forEach(function(b){b.addEventListener("click",function(e){e.stopPropagation();var k=b.dataset.pop;if(openPop===k){openPop=null;buildPop(null);return;}openPop=k;buildPop(k);placePop(b);});});
panel.addEventListener("click",function(e){
  var cell=e.target.closest(".sizecell");if(cell){var v=cell.dataset.v;if(F.sizes[v])delete F.sizes[v];else F.sizes[v]=1;cell.classList.toggle("on");refreshApply();render();return;}
  var cb=e.target.closest("input[type=checkbox]");if(cb){var map={colors:"colors",sizes:"sizes",materials:"materials",prices:"prices"}[openPop];var v=cb.dataset.v;if(cb.checked)F[map][v]=1;else delete F[map][v];refreshApply();render();return;}
  if(e.target.closest("[data-clear]")){F[openPop]={};buildPop(openPop);render();return;}
  if(e.target.closest("[data-apply]")){openPop=null;buildPop(null);}
});
function refreshApply(){var a=panel.querySelector("[data-apply]");if(a)a.textContent="View ("+filtered().length+")";}
document.addEventListener("click",function(e){if(openPop&&!e.target.closest(".pop")&&!e.target.closest(".fbtn[data-pop]")){openPop=null;buildPop(null);}});
document.getElementById("fFilter").addEventListener("click",function(e){e.stopPropagation();if(openPop==="colors"){openPop=null;buildPop(null);return;}openPop="colors";buildPop("colors");placePop(this);});
document.getElementById("clearAll").addEventListener("click",function(){F.colors={};F.sizes={};F.materials={};F.prices={};F.q="";document.getElementById("q").value="";render();});

/* ---------- PDP ---------- */
var lb=document.getElementById("lb"),LP=null,LSEL={},LIMGS=[],LCUR=0;
function waLink(p,sel,usd){var parts=[];for(var k in sel){if(sel[k])parts.push(k+": "+sel[k]);}var msg="Hello "+BRAND+"! I'm interested in this piece:\n• "+p.name+(parts.length?" ("+parts.join(", ")+")":"")+(usd!=null?"\n• Price: "+money(usd)+(cur!=="USD"?" (approx, ≈ $"+usd+")":""):"")+"\n• Ref: "+p.id+"\n\nIs it available?";return "https://wa.me/"+WHATSAPP+"?text="+encodeURIComponent(msg);}
function gshow(i){if(!LIMGS.length)return;var n=LIMGS.length;LCUR=(i%n+n)%n;document.getElementById("gimg").innerHTML='<img src="'+LIMGS[LCUR]+'" alt="">';[].forEach.call(document.getElementById("gthumbs").children,function(t,j){t.classList.toggle("on",j===LCUR);});}
function applyVariant(){
  var v=matchVar(LP,LSEL);LIMGS=v.imgs||[];
  var gt=document.getElementById("gthumbs"),multi=LIMGS.length>1;
  gt.innerHTML=LIMGS.map(function(u,j){return '<img src="'+u+'" data-j="'+j+'" alt="">';}).join("");
  document.getElementById("gp").style.display=multi?"block":"none";document.getElementById("gn").style.display=multi?"block":"none";
  gshow(0);
  var msel={};for(var mk in v.sel)msel[mk]=v.sel[mk];for(var lk in LSEL)msel[lk]=LSEL[lk];
  var pr=v.usd!=null?money(v.usd):"Enquire for price";
  var was=v.orig?'<span class="was">'+esc(money(v.orig))+'</span>':'';
  var save=v.orig&&v.usd?'<span class="save">Save '+esc(money(v.orig-v.usd))+'</span>':'';
  document.getElementById("pprice").innerHTML=was+esc(pr)+save;
  var cta=document.getElementById("pcta");cta.innerHTML=WA+"Enquire on WhatsApp";cta.onclick=function(){window.open(waLink(LP,msel,v.usd),"_blank");};
}
function buildOpts(){
  var box=document.getElementById("popts");box.innerHTML="";
  (LP.options||[]).forEach(function(o){
    var free=optIsFree(LP,o.name);
    var row=document.createElement("div");row.className="orow";
    var l=document.createElement("div");l.className="l";l.innerHTML=o.name+"<b>"+esc(LSEL[o.name]||"")+"</b>";row.appendChild(l);
    var wrap=document.createElement("div");wrap.className=(o.type==="swatch"?"bsw":"pills");
    o.values.forEach(function(x){
      var avail=true;if(!free){var t=boundSel(LP,LSEL);t[o.name]=x.label;avail=hasVariant(LP,t);}
      var el;
      if(o.type==="swatch"){el=document.createElement("span");el.className="s";el.title=x.label;el.style.background=x.hex||"#ccc";}
      else{el=document.createElement("button");el.className="pill";el.textContent=x.label;}
      if(LSEL[o.name]===x.label)el.classList.add("on");
      if(!avail&&o.type!=="swatch")el.setAttribute("disabled","");
      el.addEventListener("click",function(){
        LSEL[o.name]=x.label;
        if(!free&&!hasVariant(LP,boundSel(LP,LSEL))){var keep={};(LP.options||[]).forEach(function(oo){if(optIsFree(LP,oo.name)&&LSEL[oo.name])keep[oo.name]=LSEL[oo.name];});var v=matchVar(LP,LSEL);LSEL={};for(var k in v.sel)LSEL[k]=v.sel[k];for(var fk in keep)LSEL[fk]=keep[fk];}
        buildOpts();applyVariant();
      });
      wrap.appendChild(el);
    });
    row.appendChild(wrap);box.appendChild(row);
  });
}
function openPDP(p,ci){
  LP=p;LSEL={};var v0=firstVar(p);for(var k in v0.sel)LSEL[k]=v0.sel[k];
  var co=colorOpt(p);if(co&&ci&&co.values[ci])LSEL[co.name]=co.values[ci].label;
  document.getElementById("pcat").textContent=p.cat;
  document.getElementById("pname").textContent=p.name;
  document.getElementById("prate").innerHTML=p.rating?STAR+esc(p.rating.toFixed(1))+(p.reviews?' <span style="color:var(--faint)">('+p.reviews+' reviews)</span>':''):"";
  var acc=document.getElementById("pacc");document.getElementById("pdetails").textContent=p.details||"";acc.style.display=(p.details||"").trim()?"block":"none";acc.classList.remove("open");
  buildOpts();applyVariant();
  lb.classList.add("open");document.body.style.overflow="hidden";
}
function closePDP(){lb.classList.remove("open");document.body.style.overflow="";}
document.getElementById("pclose").addEventListener("click",closePDP);
lb.addEventListener("click",function(e){if(e.target===lb||e.target.classList.contains("lb-scroll"))closePDP();});
document.getElementById("gp").addEventListener("click",function(){gshow(LCUR-1);});
document.getElementById("gn").addEventListener("click",function(){gshow(LCUR+1);});
document.getElementById("gthumbs").addEventListener("click",function(e){var t=e.target.closest("img[data-j]");if(t)gshow(+t.dataset.j);});
document.getElementById("paccBtn").addEventListener("click",function(){document.getElementById("pacc").classList.toggle("open");});
document.addEventListener("keydown",function(e){if(!lb.classList.contains("open"))return;if(e.key==="Escape")closePDP();if(e.key==="ArrowRight")gshow(LCUR+1);if(e.key==="ArrowLeft")gshow(LCUR-1);});

/* ---------- misc ---------- */
document.getElementById("q").addEventListener("input",function(){F.q=this.value;render();});
document.getElementById("sort").addEventListener("change",function(){F.sort=this.value;render();});
document.getElementById("curBtn").addEventListener("click",cycleCur);
var waMsg="https://wa.me/"+WHATSAPP+"?text="+encodeURIComponent("Hello "+BRAND+"! I have a question about your jewelry.");
document.getElementById("waTop").addEventListener("click",function(){window.open(waMsg,"_blank");});
document.getElementById("fwa").href=waMsg;
document.getElementById("curLbl").textContent=cur;
loadRates(function(){render();});detect();
</script>
"""


def build(products, brand, whatsapp):
    return (TEMPLATE.replace("__PRODUCTS__", json.dumps(products, ensure_ascii=False))
            .replace("__WHATSAPP__", re.sub(r"\D", "", whatsapp))
            .replace("__BRAND__", html.escape(brand)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand", default="SRX DIAMONDS")
    ap.add_argument("--whatsapp", default="919723891732")
    a = ap.parse_args()
    products = json.load(open(a.data, encoding="utf-8"))
    Path(a.out).write_text(build(products, a.brand, a.whatsapp), encoding="utf-8")
    print(f"built {a.out}: {len(products)} designs")


if __name__ == "__main__":
    main()
