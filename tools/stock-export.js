/*
 * stock-export.js — pull the full stock list out of https://srx-stock.web.app/
 * and print it in a format you can paste straight into a chat.
 *
 * Usage: open the site, open DevTools (F12) -> Console, paste this whole file,
 * press Enter. Chrome may ask you to type "allow pasting" first.
 *
 * It loads everything (scrolls, clicks "load more"), then tries three sources in
 * order: the Firestore offline cache, an HTML <table>, then a repeated card/grid
 * layout. Whichever works first wins.
 *
 * After it runs, __srx is left on the page:
 *   __srx.rows              the extracted rows as objects
 *   __srx.md()              markdown table   (good for an AI chat)
 *   __srx.txt()             plain lines      (good for WhatsApp/SMS)
 *   __srx.csv()             CSV              (good for Sheets/Excel)
 *   __srx.json()            JSON
 *   __srx.copy('txt')       copy that format to the clipboard
 *   __srx.download('csv')   save it as a file
 * Pass true as the last argument to any of them to include hidden columns
 * (image URLs, internal ids): __srx.csv(true), __srx.copy('json', true).
 */

(async () => {
  'use strict';

  // The DevTools `copy()` helper isn't on window, so grab it while we're still
  // in the console's scope. Not every browser has it.
  let consoleCopy = null;
  try { consoleCopy = typeof copy === 'function' ? copy : null; } catch (_) { /* no console API */ }

  const CFG = {
    autoScroll: true,      // scroll to pull in lazily-rendered rows
    maxScrollRounds: 40,
    clickLoadMore: true,   // click "load more" style buttons while scrolling
    maxLoadMoreClicks: 30,
    minRows: 3,            // fewer than this and we don't believe it's the list
  };

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const txt = (el) => ((el && (el.innerText || el.textContent)) || '').replace(/\s+/g, ' ').trim();
  const visible = (el) => !!(el.offsetParent || el.getClientRects().length);

  /* ------------------------------------------------------------------ *
   * 1. Get everything onto the page first
   * ------------------------------------------------------------------ */

  async function loadEverything() {
    if (!CFG.autoScroll) return;
    const countable = 'tr, li, [class*=card], [class*=item], [class*=row], [class*=product]';
    let last = -1;
    let stable = 0;
    let clicks = 0;

    for (let i = 0; i < CFG.maxScrollRounds && stable < 3; i++) {
      for (const el of document.querySelectorAll('*')) {
        if (el.scrollHeight > el.clientHeight + 50) el.scrollTop = el.scrollHeight;
      }
      window.scrollTo(0, document.body.scrollHeight);

      if (CFG.clickLoadMore && clicks < CFG.maxLoadMoreClicks) {
        const btn = [...document.querySelectorAll('button, a, [role=button]')].find(
          (b) => visible(b) && /\b(load|show|see|view)\s+(more|all)\b/i.test(txt(b))
        );
        if (btn) { btn.click(); clicks++; }
      }

      await sleep(400);
      const n = document.querySelectorAll(countable).length;
      if (n === last) stable++;
      else { stable = 0; last = n; }
    }
    window.scrollTo(0, 0);
  }

  /* ------------------------------------------------------------------ *
   * 2. Source A — the Firestore offline cache
   * Most reliable when it exists: it holds every document, not just the
   * page you happen to be looking at. Only present if the app turned on
   * offline persistence.
   * ------------------------------------------------------------------ */

  function decodeValue(v) {
    if (v === null || typeof v !== 'object') return v;
    if ('stringValue' in v) return v.stringValue;
    if ('integerValue' in v) return Number(v.integerValue);
    if ('doubleValue' in v) return Number(v.doubleValue);
    if ('booleanValue' in v) return v.booleanValue;
    if ('nullValue' in v) return null;
    if ('timestampValue' in v) {
      const t = v.timestampValue;
      return typeof t === 'string' ? t : new Date(Number(t.seconds || 0) * 1000).toISOString();
    }
    if ('arrayValue' in v) return ((v.arrayValue && v.arrayValue.values) || []).map(decodeValue);
    if ('mapValue' in v) return decodeFields((v.mapValue && v.mapValue.fields) || {});
    if ('referenceValue' in v) return v.referenceValue;
    if ('geoPointValue' in v) return `${v.geoPointValue.latitude},${v.geoPointValue.longitude}`;
    if ('bytesValue' in v) return '[bytes]';
    return v;
  }

  function decodeFields(fields) {
    const out = {};
    for (const [k, v] of Object.entries(fields)) out[k] = decodeValue(v);
    return out;
  }

  const openDB = (name) => new Promise((res, rej) => {
    const req = indexedDB.open(name);
    req.onsuccess = () => res(req.result);
    req.onerror = () => rej(req.error);
    req.onblocked = () => rej(new Error('blocked'));
  });

  const readAll = (db, store) => new Promise((res, rej) => {
    const req = db.transaction(store, 'readonly').objectStore(store).getAll();
    req.onsuccess = () => res(req.result || []);
    req.onerror = () => rej(req.error);
  });

  async function fromFirestore() {
    // No IndexedDB in Safari private browsing, and .databases() is not universal.
    if (typeof indexedDB === 'undefined' || !indexedDB || !indexedDB.databases) return null;
    let names = [];
    try {
      names = (await indexedDB.databases()).map((d) => d.name).filter((n) => n && /firestore/i.test(n));
    } catch (_) { return null; }

    const byCollection = new Map();

    for (const name of names) {
      let db;
      try { db = await openDB(name); } catch (_) { continue; }
      const stores = [...db.objectStoreNames].filter((s) => /remoteDocument/i.test(s));
      for (const store of stores) {
        let recs = [];
        try { recs = await readAll(db, store); } catch (_) { continue; }
        for (const rec of recs) {
          const doc = rec && (rec.document || rec);
          if (!doc || !doc.fields || typeof doc.name !== 'string') continue;
          const path = doc.name.split('/documents/')[1];
          if (!path) continue;
          const parts = path.split('/');
          const id = parts.pop();
          const collection = parts.join('/');
          if (!byCollection.has(collection)) byCollection.set(collection, []);
          byCollection.get(collection).push({ ...decodeFields(doc.fields), _id: id });
        }
      }
      db.close();
    }

    if (!byCollection.size) return null;

    // Prefer a collection that sounds like stock; otherwise take the biggest.
    const entries = [...byCollection.entries()];
    const named = entries.filter(([c]) => /stock|item|product|jewel|inventor|design|piece/i.test(c));
    const [collection, rows] = (named.length ? named : entries).sort((a, b) => b[1].length - a[1].length)[0];
    if (rows.length < CFG.minRows) return null;
    return { rows, source: `Firestore cache (collection "${collection}")` };
  }

  /* ------------------------------------------------------------------ *
   * 3. Source B — an HTML table
   * ------------------------------------------------------------------ */

  function fromTables() {
    let best = null;
    for (const t of document.querySelectorAll('table')) {
      const trs = [...t.querySelectorAll('tr')].filter((tr) => tr.querySelector('td, th'));
      if (!best || trs.length > best.trs.length) best = { t, trs };
    }
    if (!best || best.trs.length < CFG.minRows) return null;

    const headRow = best.t.querySelector('thead tr') || best.trs[0];
    const headers = [...headRow.children].map((c, i) => txt(c) || `Column ${i + 1}`);
    const body = best.trs.filter((tr) => tr !== headRow && !tr.closest('thead') && !tr.closest('tfoot'));
    if (body.length < CFG.minRows) return null;

    const rows = body.map((tr) => {
      const row = {};
      [...tr.children].forEach((cell, i) => {
        const key = headers[i] || `Column ${i + 1}`;
        row[key] = txt(cell);
        const img = cell.querySelector('img[src]');
        if (img && !row._image) row._image = img.src;
      });
      return row;
    });

    return { rows, source: 'HTML table' };
  }

  /* ------------------------------------------------------------------ *
   * 4. Source C — a repeated card / grid / list layout
   * Find the container whose children repeat the most with the most text
   * in them; that's almost always the list.
   * ------------------------------------------------------------------ */

  const signature = (el) => `${el.tagName}|${[...el.classList].slice(0, 3).sort().join('.')}`;

  function fromCards() {
    const candidates = [];

    for (const el of document.body.querySelectorAll('*')) {
      const kids = [...el.children].filter(visible);
      if (kids.length < CFG.minRows) continue;

      const counts = new Map();
      for (const k of kids) counts.set(signature(k), (counts.get(signature(k)) || 0) + 1);
      const [topSig, n] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
      if (n < CFG.minRows) continue;

      const items = kids.filter((k) => signature(k) === topSig);
      const avgLen = items.reduce((s, k) => s + txt(k).length, 0) / items.length;
      if (avgLen < 8) continue;

      candidates.push({ items, score: n * Math.min(avgLen, 300) });
    }

    if (!candidates.length) return null;
    candidates.sort((a, b) => b.score - a.score);

    const rows = candidates[0].items.map(itemFields);
    return { rows, source: 'repeated card / list layout' };
  }

  // innerText is what we want — it respects hidden elements and gives us the
  // line breaks the user actually sees — but it isn't everywhere, so fall back
  // to walking text nodes.
  function linesOf(el) {
    if (typeof el.innerText === 'string') {
      return el.innerText.split('\n').map((s) => s.trim()).filter(Boolean);
    }
    const out = [];
    (function walk(node) {
      for (const child of node.childNodes) {
        if (child.nodeType === 3) {
          const t = child.textContent.replace(/\s+/g, ' ').trim();
          if (t) out.push(t);
        } else if (child.nodeType === 1) {
          walk(child);
        }
      }
    })(el);
    return out;
  }

  function itemFields(el) {
    const row = {};
    let unlabelled = 0;

    // Definition lists and explicitly labelled cells come out clean.
    for (const dt of el.querySelectorAll('dt')) {
      const dd = dt.nextElementSibling;
      if (dd && dd.tagName === 'DD') row[txt(dt).replace(/[:：]$/, '')] = txt(dd);
    }
    for (const cell of el.querySelectorAll('[data-label], [data-title]')) {
      const key = cell.getAttribute('data-label') || cell.getAttribute('data-title');
      if (key) row[key.trim()] = txt(cell);
    }

    // Otherwise walk the visible lines, splitting "Label: value" where we see it.
    for (const line of linesOf(el)) {
      const m = line.match(/^([A-Za-z][\w .%/#()&-]{0,28}?)\s*[:：]\s*(.+)$/);
      if (m) {
        const key = m[1].trim();
        if (!(key in row)) row[key] = m[2].trim();
      } else {
        row[`col${++unlabelled}`] = line;
      }
    }

    const img = el.querySelector('img[src]');
    if (img) row._image = img.src;
    const link = el.querySelector('a[href]');
    if (link) row._link = link.href;

    return row;
  }

  /* ------------------------------------------------------------------ *
   * 5. Tidy up the rows
   * ------------------------------------------------------------------ */

  function clean(rows) {
    // Union of every key, in first-seen order, so ragged rows still line up.
    const cols = [];
    for (const r of rows) for (const k of Object.keys(r)) if (!cols.includes(k)) cols.push(k);

    const keep = cols.filter((c) => {
      if (c.startsWith('_')) return true;                       // hidden, but kept
      if (/^(actions?|edit|delete|remove|select|·|\.\.\.)$/i.test(c)) return false;
      const filled = rows.filter((r) => r[c] != null && String(r[c]).trim() !== '').length;
      return filled / rows.length >= 0.2;                        // drop near-empty columns
    });

    // The first unlabelled column is nearly always the item name.
    const rename = {};
    if (keep.includes('col1')) rename.col1 = 'Item';

    return rows.map((r) => {
      const out = {};
      for (const c of keep) {
        const v = r[c];
        out[rename[c] || c] = v == null ? '' : Array.isArray(v) ? v.join(', ')
          : typeof v === 'object' ? JSON.stringify(v) : String(v);
      }
      return out;
    });
  }

  /* ------------------------------------------------------------------ *
   * 6. Formatters
   * ------------------------------------------------------------------ */

  const columnsOf = (rows, full) => {
    const cols = [];
    for (const r of rows) for (const k of Object.keys(r)) if (!cols.includes(k)) cols.push(k);
    return full ? cols : cols.filter((c) => !c.startsWith('_'));
  };

  const csvCell = (v) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);

  function toCSV(rows, full) {
    const cols = columnsOf(rows, full);
    return [cols.map(csvCell).join(','), ...rows.map((r) => cols.map((c) => csvCell(r[c] || '')).join(','))].join('\n');
  }

  function toMarkdown(rows, full) {
    const cols = columnsOf(rows, full);
    const esc = (v) => String(v || '').replace(/\|/g, '\\|');
    return [
      `| ${cols.join(' | ')} |`,
      `| ${cols.map(() => '---').join(' | ')} |`,
      ...rows.map((r) => `| ${cols.map((c) => esc(r[c])).join(' | ')} |`),
    ].join('\n');
  }

  function toText(rows, full) {
    const cols = columnsOf(rows, full);
    const [first, ...rest] = cols;
    return rows
      .map((r, i) => {
        const detail = rest.filter((c) => r[c]).map((c) => `${c}: ${r[c]}`).join(' · ');
        return `${i + 1}. ${r[first] || '(no name)'}${detail ? ` — ${detail}` : ''}`;
      })
      .join('\n');
  }

  function toJSON(rows, full) {
    const cols = columnsOf(rows, full);
    return JSON.stringify(rows.map((r) => Object.fromEntries(cols.map((c) => [c, r[c]]))), null, 2);
  }

  /* ------------------------------------------------------------------ *
   * Run
   * ------------------------------------------------------------------ */

  console.log('%c[srx] loading the full list…', 'color:#888');
  await loadEverything();

  let result = null;
  for (const strategy of [fromFirestore, fromTables, fromCards]) {
    try {
      result = await strategy();
    } catch (err) {
      console.warn(`[srx] ${strategy.name} failed:`, err);
      result = null;
    }
    if (result && result.rows.length >= CFG.minRows) break;
    result = null;
  }

  const rows = result ? clean(result.rows) : [];

  if (!rows.length || !columnsOf(rows, false).length) {
    console.error(
      '[srx] Could not find a list on this page.\n' +
      'Navigate to the screen that shows your stock, then paste this again.'
    );
    return;
  }

  const api = {
    rows,
    source: result.source,
    md: (full) => toMarkdown(rows, full),
    txt: (full) => toText(rows, full),
    csv: (full) => toCSV(rows, full),
    json: (full) => toJSON(rows, full),
    copy(fmt = 'md', full = false) {
      const s = api[fmt](full);
      if (consoleCopy) { consoleCopy(s); console.log(`[srx] copied ${fmt} (${rows.length} rows)`); return; }
      if (!navigator.clipboard) { console.log(`[srx] no clipboard here — copy manually:\n\n${s}`); return; }
      navigator.clipboard.writeText(s).then(
        () => console.log(`[srx] copied ${fmt} (${rows.length} rows)`),
        () => console.log(`[srx] clipboard blocked — here it is, copy manually:\n\n${s}`)
      );
    },
    download(fmt = 'csv', full = false) {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([api[fmt](full)], { type: 'text/plain;charset=utf-8' }));
      a.download = `srx-stock.${fmt === 'txt' ? 'txt' : fmt}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    },
  };

  window.__srx = api;

  console.log(`%c[srx] ${rows.length} rows from ${result.source}`, 'color:#0a0;font-weight:bold');
  console.table(rows.slice(0, 10));
  console.log(api.md());
  console.log(
    '%c[srx] __srx.copy("md" | "txt" | "csv" | "json")  ·  __srx.download("csv")  ·  __srx.rows',
    'color:#888'
  );
  api.copy('md');
})();
