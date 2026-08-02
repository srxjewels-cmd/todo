#!/usr/bin/env node
/*
 * vdb-to-chat.mjs — pull your VDB (Virtual Diamond Boutique) inventory and
 * print it in a form you can paste straight into a chat.
 *
 * Run this on your own machine, not in a Claude session — VDB's hosts are
 * blocked by the sandbox's egress policy. Needs Node 18+ (for global fetch)
 * and no packages.
 *
 * VDB does not publish its API schema, so nothing here is hard-coded to a
 * guessed response shape. Start with --probe: it makes one request and tells
 * you where the items actually live and what fields they carry. Everything
 * after that adapts to what it finds.
 *
 *   export VDB_API_KEY=...                     # never commit this
 *   node vdb-to-chat.mjs --probe               # see the real response shape
 *   node vdb-to-chat.mjs --format md           # markdown table, for an AI chat
 *   node vdb-to-chat.mjs --format txt          # plain lines, for a customer
 *   node vdb-to-chat.mjs --format csv --out stock.csv
 *
 * Endpoint and auth are configurable because they vary by VDB account tier:
 *
 *   --base https://api.vdbapp.com     VDB_API_BASE
 *   --endpoint /v1/diamonds           VDB_ENDPOINT
 *   --auth bearer                     VDB_AUTH   bearer | basic
 *                                                header:X-Api-Key | query:api_key
 *
 * Other flags:
 *   --fields a,b,c    columns to keep, in order (accepts name:Label to rename)
 *   --all-fields      keep every field instead of the useful-looking ones
 *   --limit N         stop after N items
 *   --page-size N     items per request (default 100)
 *   --max-pages N     safety stop (default 200)
 *   --param k=v       extra query parameter, repeatable (filters, sort, …)
 *   --raw             dump the collected items as raw JSON
 *   --out FILE        write to a file instead of stdout
 */

import { writeFileSync, readFileSync, realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

/* -------------------------------------------------------------------- *
 * Config
 * -------------------------------------------------------------------- */

export const DEFAULTS = {
  base: process.env.VDB_API_BASE || 'https://api.vdbapp.com',
  endpoint: process.env.VDB_ENDPOINT || '/v1/diamonds',
  auth: process.env.VDB_AUTH || 'bearer',
  key: process.env.VDB_API_KEY || '',
  format: 'md',
  pageSize: 100,
  maxPages: 200,
  pageParam: 'page',
  sizeParam: 'per_page',
  limit: 0,
  fields: null,
  allFields: false,
  params: {},
  probe: false,
  raw: false,
  out: null,
};

function parseArgs(argv) {
  const cfg = { ...DEFAULTS, params: { ...DEFAULTS.params } };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    switch (a) {
      case '--base': cfg.base = next(); break;
      case '--endpoint': cfg.endpoint = next(); break;
      case '--auth': cfg.auth = next(); break;
      case '--format': cfg.format = next(); break;
      case '--fields': cfg.fields = next().split(',').map((s) => s.trim()).filter(Boolean); break;
      case '--all-fields': cfg.allFields = true; break;
      case '--limit': cfg.limit = Number(next()); break;
      case '--page-size': cfg.pageSize = Number(next()); break;
      case '--max-pages': cfg.maxPages = Number(next()); break;
      case '--page-param': cfg.pageParam = next(); break;
      case '--size-param': cfg.sizeParam = next(); break;
      case '--param': { const [k, ...v] = next().split('='); cfg.params[k] = v.join('='); break; }
      case '--probe': cfg.probe = true; break;
      case '--raw': cfg.raw = true; break;
      case '--out': cfg.out = next(); break;
      case '-h': case '--help': cfg.help = true; break;
      default: throw new Error(`Unknown option: ${a}  (try --help)`);
    }
  }
  return cfg;
}

/* -------------------------------------------------------------------- *
 * HTTP
 * -------------------------------------------------------------------- */

export function authFor(cfg) {
  const headers = {};
  let queryParam = null;
  if (cfg.auth === 'bearer') headers.Authorization = `Bearer ${cfg.key}`;
  else if (cfg.auth === 'basic') headers.Authorization = `Basic ${Buffer.from(cfg.key).toString('base64')}`;
  else if (cfg.auth.startsWith('header:')) headers[cfg.auth.slice(7)] = cfg.key;
  else if (cfg.auth.startsWith('query:')) queryParam = cfg.auth.slice(6);
  else throw new Error(`Unrecognised --auth "${cfg.auth}" (bearer | basic | header:NAME | query:NAME)`);
  return { headers, queryParam };
}

export function buildUrl(cfg, extra = {}) {
  const url = new URL(cfg.endpoint, cfg.base);
  for (const [k, v] of Object.entries({ ...cfg.params, ...extra })) {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  }
  if (cfg._auth.queryParam) url.searchParams.set(cfg._auth.queryParam, cfg.key);
  return url.toString();
}

// Never let the key reach a log line or an error message.
export const redact = (s, cfg) => (cfg.key ? String(s).split(cfg.key).join('«KEY»') : String(s));

export async function get(url, cfg) {
  let res;
  try {
    res = await fetch(url, { headers: { Accept: 'application/json', ...cfg._auth.headers } });
  } catch (err) {
    throw new Error(
      `Could not reach ${redact(url, cfg)}\n${err.message}\n` +
      'If you are running this inside a Claude sandbox, that is expected — VDB is blocked there. Run it locally.'
    );
  }
  const text = await res.text();
  if (!res.ok) {
    const hint = res.status === 401 || res.status === 403
      ? '\nCheck VDB_API_KEY and --auth: VDB may expect header:X-Api-Key rather than bearer.'
      : res.status === 404
        ? '\nCheck --endpoint. --probe against the path VDB gave you for your tier.'
        : '';
    throw new Error(`HTTP ${res.status} ${res.statusText} from ${redact(url, cfg)}${hint}\n${redact(text.slice(0, 600), cfg)}`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Expected JSON, got:\n${redact(text.slice(0, 300), cfg)}`);
  }
}

/* -------------------------------------------------------------------- *
 * Shape discovery — find the item array wherever the API happens to put it
 * -------------------------------------------------------------------- */

export function findItems(json) {
  let best = null;
  const seen = new Set();

  (function walk(node, path, depth) {
    if (!node || typeof node !== 'object' || depth > 8 || seen.has(node)) return;
    seen.add(node);

    if (Array.isArray(node)) {
      const objs = node.filter((x) => x && typeof x === 'object' && !Array.isArray(x));
      if (objs.length && (!best || objs.length > best.items.length)) best = { items: objs, path: path || '(root)' };
      node.slice(0, 3).forEach((v, i) => walk(v, `${path}[${i}]`, depth + 1)); // sample, don't scan
      return;
    }
    for (const [k, v] of Object.entries(node)) walk(v, path ? `${path}.${k}` : k, depth + 1);
  })(json, '', 0);

  return best;
}

export function nextUrl(json) {
  const candidates = [
    json?.next, json?.next_page_url, json?.nextPageUrl,
    json?.links?.next, json?.paging?.next, json?.meta?.next, json?._links?.next?.href,
  ];
  for (const c of candidates) {
    if (typeof c === 'string' && /^https?:/i.test(c)) return c;
    if (c && typeof c === 'object' && typeof c.href === 'string' && /^https?:/i.test(c.href)) return c.href;
  }
  return null;
}

export function flatten(obj, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
    else if (Array.isArray(v)) out[key] = v.map((x) => (x && typeof x === 'object' ? JSON.stringify(x) : String(x))).join(', ');
    else out[key] = v == null ? '' : String(v);
  }
  return out;
}

/* -------------------------------------------------------------------- *
 * Fetching
 * -------------------------------------------------------------------- */

export async function fetchAll(cfg, onPage = () => {}) {
  const rows = [];
  let page = 1;
  let url = buildUrl(cfg, { [cfg.pageParam]: page, [cfg.sizeParam]: cfg.pageSize });

  for (let n = 0; n < cfg.maxPages && url; n++) {
    const json = await get(url, cfg);
    const found = findItems(json);
    if (!found || !found.items.length) break;

    rows.push(...found.items.map((o) => flatten(o)));
    onPage(rows.length, found);

    if (cfg.limit && rows.length >= cfg.limit) break;

    const link = nextUrl(json);
    if (link) { url = link; continue; }
    if (found.items.length < cfg.pageSize) break;   // short page means we're done
    page += 1;
    url = buildUrl(cfg, { [cfg.pageParam]: page, [cfg.sizeParam]: cfg.pageSize });
  }

  return cfg.limit ? rows.slice(0, cfg.limit) : rows;
}

/* -------------------------------------------------------------------- *
 * Column selection
 * -------------------------------------------------------------------- */

// Ordered by how much a jeweller actually wants to see them in a chat.
export const PREFERRED = [
  'stock_number', 'stock_no', 'stocknumber', 'sku', 'item_number', 'lot',
  'shape', 'carat', 'carats', 'weight', 'size',
  'color', 'colour', 'clarity', 'cut', 'cut_grade',
  'polish', 'symmetry', 'fluorescence', 'fluor',
  'lab', 'certificate_number', 'cert_number', 'report_number', 'certificate',
  'measurements', 'depth', 'depth_percent', 'table', 'table_percent',
  'price', 'total_price', 'amount', 'price_per_carat', 'ppc', 'rap', 'discount', 'rap_discount',
  'availability', 'status', 'location', 'country', 'seller', 'supplier', 'vendor',
];

const NOISY = /(^|[._])(id|uuid|guid|_?url|href|image|images|photo|video|thumbnail|token|created_?at|updated_?at|deleted_?at|timestamp)$/i;

export const leaf = (k) => k.split('.').pop().toLowerCase();

export function selectColumns(rows, cfg) {
  const all = [];
  for (const r of rows) for (const k of Object.keys(r)) if (!all.includes(k)) all.push(k);

  if (cfg.fields) {
    return cfg.fields.map((f) => {
      const [name, label] = f.split(':');
      const match = all.find((c) => c === name) || all.find((c) => leaf(c) === name.toLowerCase());
      return { key: match || name, label: label || match || name };
    });
  }

  const filled = (c) => rows.filter((r) => r[c] != null && r[c] !== '').length / rows.length;
  const usable = all.filter((c) => filled(c) >= 0.1);

  if (cfg.allFields) return usable.map((c) => ({ key: c, label: c }));

  const ranked = [...usable].sort((a, b) => {
    const ia = PREFERRED.indexOf(leaf(a));
    const ib = PREFERRED.indexOf(leaf(b));
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });

  const hits = ranked.filter((c) => PREFERRED.includes(leaf(c)));
  const rest = ranked.filter((c) => !PREFERRED.includes(leaf(c)) && !NOISY.test(c));
  const chosen = (hits.length ? hits : rest).slice(0, 14);

  return chosen.map((c) => ({ key: c, label: leaf(c).replace(/_/g, ' ') }));
}

/* -------------------------------------------------------------------- *
 * Formatters — same output shapes as tools/stock-export.js
 * -------------------------------------------------------------------- */

const csvCell = (v) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
const cell = (row, c) => (row[c.key] == null ? '' : String(row[c.key]));

export const toCSV = (rows, cols) =>
  [cols.map((c) => csvCell(c.label)).join(','), ...rows.map((r) => cols.map((c) => csvCell(cell(r, c))).join(','))].join('\n');

export const toMarkdown = (rows, cols) =>
  [
    `| ${cols.map((c) => c.label).join(' | ')} |`,
    `| ${cols.map(() => '---').join(' | ')} |`,
    ...rows.map((r) => `| ${cols.map((c) => cell(r, c).replace(/\|/g, '\\|')).join(' | ')} |`),
  ].join('\n');

export const toText = (rows, cols) => {
  const [first, ...rest] = cols;
  return rows
    .map((r, i) => {
      const detail = rest.filter((c) => cell(r, c)).map((c) => `${c.label}: ${cell(r, c)}`).join(' · ');
      return `${i + 1}. ${cell(r, first) || '(no name)'}${detail ? ` — ${detail}` : ''}`;
    })
    .join('\n');
};

export const toJSON = (rows, cols) =>
  JSON.stringify(rows.map((r) => Object.fromEntries(cols.map((c) => [c.label, cell(r, c)]))), null, 2);

/* -------------------------------------------------------------------- *
 * Probe — one request, report what is actually there
 * -------------------------------------------------------------------- */

async function probe(cfg) {
  const url = buildUrl(cfg, { [cfg.pageParam]: 1, [cfg.sizeParam]: Math.min(cfg.pageSize, 5) });
  console.log(`GET ${redact(url, cfg)}`);
  console.log(`auth: ${cfg.auth}${cfg._auth.queryParam ? ` (as ?${cfg._auth.queryParam}=)` : ''}\n`);

  const json = await get(url, cfg);
  console.log(`top-level: ${Array.isArray(json) ? '(array)' : Object.keys(json).join(', ') || '(empty object)'}`);

  const found = findItems(json);
  if (!found) {
    console.log('\nNo array of objects anywhere in the response. Raw response:\n');
    console.log(JSON.stringify(json, null, 2).slice(0, 4000));
    return;
  }

  console.log(`items at: ${found.path}   (${found.items.length} on this page)`);
  console.log(`next-page link: ${nextUrl(json) || '(none — will increment ?' + cfg.pageParam + ')'}\n`);

  const flat = flatten(found.items[0]);
  console.log('fields on the first item:');
  for (const [k, v] of Object.entries(flat)) {
    const mark = PREFERRED.includes(leaf(k)) ? '*' : ' ';
    console.log(` ${mark} ${k.padEnd(34)} ${String(v).slice(0, 60)}`);
  }

  const suggested = Object.keys(flat).filter((k) => PREFERRED.includes(leaf(k)));
  console.log(`\n* = recognised. ${suggested.length ? `Default columns would be:\n  --fields ${suggested.join(',')}` : 'None recognised — pass --fields yourself, or --all-fields.'}`);
}

/* -------------------------------------------------------------------- *
 * Main
 * -------------------------------------------------------------------- */

// The header comment above is the help text; no need to write it twice.
const HELP = readFileSync(new URL(import.meta.url), 'utf8')
  .split('*/')[0]                     // just the header block
  .replace(/^[\s\S]*?\/\*\n/, '')     // drop the shebang and the comment opener
  .replace(/^ \* ?/gm, '')            // unprefix each line
  .trim();

async function main() {
  const cfg = parseArgs(process.argv.slice(2));
  if (cfg.help) { console.log(HELP); return; }

  if (!cfg.key) {
    console.error('VDB_API_KEY is not set.\n\n  export VDB_API_KEY=your-key\n\nKeep it in your shell or a secret manager — do not commit it or paste it into a chat.');
    process.exitCode = 1;
    return;
  }

  cfg._auth = authFor(cfg);

  if (cfg.probe) { await probe(cfg); return; }

  const rows = await fetchAll(cfg, (n) => process.stderr.write(`\rfetched ${n} items…`));
  process.stderr.write('\r');

  if (!rows.length) {
    console.error('No items came back. Run --probe to see what the endpoint actually returns.');
    process.exitCode = 1;
    return;
  }

  if (cfg.raw) {
    const out = JSON.stringify(rows, null, 2);
    cfg.out ? writeFileSync(cfg.out, out) : console.log(out);
    process.stderr.write(`${rows.length} items\n`);
    return;
  }

  const cols = selectColumns(rows, cfg);
  const render = { md: toMarkdown, txt: toText, csv: toCSV, json: toJSON }[cfg.format];
  if (!render) throw new Error(`Unknown --format "${cfg.format}" (md | txt | csv | json)`);

  const output = render(rows, cols);
  if (cfg.out) {
    writeFileSync(cfg.out, output);
    process.stderr.write(`${rows.length} items -> ${cfg.out}\n`);
  } else {
    console.log(output);
    process.stderr.write(`${rows.length} items, ${cols.length} columns\n`);
  }
}

// Only run when invoked directly — vdb-price-check.mjs imports the helpers above.
const invokedDirectly = process.argv[1] &&
  fileURLToPath(import.meta.url) === realpathSync(process.argv[1]);

if (invokedDirectly) {
  main().catch((err) => {
    console.error(`\n${err.message}`);
    process.exitCode = 1;
  });
}
