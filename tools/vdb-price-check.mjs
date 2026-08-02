#!/usr/bin/env node
/*
 * vdb-price-check.mjs — average per-carat price for a list of diamond specs.
 *
 * Run on your own machine (VDB is blocked inside a Claude sandbox). Node 18+,
 * no packages. Reuses the fetching and shape-discovery in vdb-to-chat.mjs.
 *
 *   export VDB_API_KEY=...
 *   node tools/vdb-price-check.mjs                     # the default spec list
 *   node tools/vdb-price-check.mjs --format md
 *   node tools/vdb-price-check.mjs --specs my.json     # your own specs
 *   node tools/vdb-price-check.mjs --show 3            # list the matched stones
 *
 * Filtering happens on the client, against the flattened fields the API
 * returns. That is deliberate: VDB does not publish its query parameter names,
 * so matching on values we can actually see is the part that doesn't break.
 * If you know the server-side filter names, push them down with --param to cut
 * the amount fetched:
 *
 *   node tools/vdb-price-check.mjs --param lab=IGI --param location=Surat
 *
 * Carat matching follows the trade sieve: "1 carat" means 1.00–1.09, "0.50"
 * means 0.50–0.59. Change the width with --carat-band.
 *
 * Flags (plus everything vdb-to-chat.mjs accepts for connection/auth):
 *   --specs FILE     JSON array of specs, replacing the built-in list
 *   --take N         how many stones to average (default 10 — "first 10")
 *   --sort FIELD     order matches before taking N (e.g. price_per_carat)
 *   --carat-band N   carat window width (default 0.10)
 *   --lab NAME       required lab (default IGI; "" for any)
 *   --location NAME  required location substring (default Surat; "" for any)
 *   --show N         also print the first N matched stones per spec
 *   --format md|csv|json
 */

import { readFileSync } from 'node:fs';
import {
  DEFAULTS, authFor, fetchAll, flatten, leaf, redact,
} from './vdb-to-chat.mjs';

/* -------------------------------------------------------------------- *
 * The specs asked for. Edit here or pass --specs your.json
 * -------------------------------------------------------------------- */

const SPECS = [
  { shape: 'Princess', color: 'F', clarity: 'VS1', carat: 1 },
  { shape: 'Emerald',  color: 'E', clarity: 'VS1', carat: 1 },
  { shape: 'Round',    color: 'F', clarity: 'VS1', carat: 1 },
  { shape: 'Oval',     color: 'F', clarity: 'VS1', carat: 1 },

  { shape: 'Cushion',  color: 'E', clarity: 'VVS2', carat: 1, ratioMin: 1.10, label: 'Cushion elongated' },
  { shape: 'Cushion',  color: 'E', clarity: 'VVS2', carat: 2, ratioMin: 1.10, label: 'Cushion elongated' },
  { shape: 'Round',    color: 'E', clarity: 'VVS2', carat: 1 },
  { shape: 'Round',    color: 'E', clarity: 'VVS2', carat: 0.5 },
  { shape: 'Emerald',  color: 'E', clarity: 'VVS2', carat: 1 },
  { shape: 'Emerald',  color: 'E', clarity: 'VVS2', carat: 2 },
  { shape: 'Radiant',  color: 'E', clarity: 'VVS2', carat: 1 },
  { shape: 'Radiant',  color: 'E', clarity: 'VVS2', carat: 2 },
];

/* -------------------------------------------------------------------- *
 * Locate the fields we need among whatever the API returned
 * -------------------------------------------------------------------- */

const ALIASES = {
  shape:     ['shape', 'cut_shape', 'stone_shape'],
  color:     ['color', 'colour', 'color_grade'],
  clarity:   ['clarity', 'clarity_grade'],
  carat:     ['carat', 'carats', 'weight', 'carat_weight', 'size'],
  lab:       ['lab', 'laboratory', 'certificate_lab', 'cert_lab', 'grading_lab'],
  location:  ['location', 'city', 'country', 'stock_location', 'warehouse'],
  total:     ['total_price', 'price', 'amount', 'total', 'net_value'],
  perCarat:  ['price_per_carat', 'ppc', 'per_carat', 'price_carat', 'rap_price'],
  ratio:     ['ratio', 'lw_ratio', 'length_width_ratio'],
  measure:   ['measurements', 'measurement', 'dimensions'],
  stock:     ['stock_number', 'stock_no', 'sku', 'item_number', 'lot'],
};

function resolveFields(rows) {
  const keys = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const found = {};
  for (const [name, aliases] of Object.entries(ALIASES)) {
    // Prefer an exact leaf match, then a substring match, shortest key first.
    found[name] =
      keys.find((k) => aliases.includes(leaf(k))) ||
      keys.filter((k) => aliases.some((a) => leaf(k).includes(a))).sort((a, b) => a.length - b.length)[0] ||
      null;
  }
  return found;
}

/* -------------------------------------------------------------------- *
 * Matching
 * -------------------------------------------------------------------- */

const num = (v) => {
  const n = Number(String(v ?? '').replace(/[^0-9.\-]/g, ''));
  return Number.isFinite(n) ? n : null;
};

const norm = (v) => String(v ?? '').trim().toLowerCase();

// "Cushion Modified Brilliant" should match a Cushion spec; "Square Radiant"
// should match Radiant. Substring either way, so both spellings work.
function shapeMatches(rowShape, wanted) {
  const a = norm(rowShape);
  const b = norm(wanted);
  return a === b || a.includes(b) || b.includes(a);
}

// Length-to-width, from an explicit field or parsed out of "7.21x5.10x3.40".
function ratioOf(row, f) {
  if (f.ratio && num(row[f.ratio])) return num(row[f.ratio]);
  if (!f.measure) return null;
  const parts = String(row[f.measure] ?? '').split(/[x×*]/).map((s) => num(s)).filter(Boolean);
  if (parts.length < 2) return null;
  const [l, w] = [Math.max(parts[0], parts[1]), Math.min(parts[0], parts[1])];
  return w ? l / w : null;
}

function matches(row, spec, f, cfg) {
  if (f.shape && !shapeMatches(row[f.shape], spec.shape)) return false;
  if (f.color && norm(row[f.color]) !== norm(spec.color)) return false;
  if (f.clarity && norm(row[f.clarity]) !== norm(spec.clarity)) return false;

  if (f.carat) {
    const ct = num(row[f.carat]);
    if (ct === null || ct < spec.carat || ct >= spec.carat + cfg.caratBand) return false;
  }
  if (cfg.lab && f.lab && !norm(row[f.lab]).includes(norm(cfg.lab))) return false;
  if (cfg.location && f.location && !norm(row[f.location]).includes(norm(cfg.location))) return false;

  if (spec.ratioMin) {
    const r = ratioOf(row, f);
    if (r === null || r < spec.ratioMin) return false;
  }
  return true;
}

function perCarat(row, f) {
  const direct = f.perCarat ? num(row[f.perCarat]) : null;
  if (direct) return direct;
  const total = f.total ? num(row[f.total]) : null;
  const ct = f.carat ? num(row[f.carat]) : null;
  return total && ct ? total / ct : null;
}

/* -------------------------------------------------------------------- *
 * Stats
 * -------------------------------------------------------------------- */

const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

const money = (n) => (n === null ? '—' : `$${Math.round(n).toLocaleString('en-US')}`);

function analyse(rows, spec, f, cfg) {
  let hits = rows.filter((r) => matches(r, spec, f, cfg));

  if (cfg.sort) {
    const key = Object.keys(hits[0] ?? {}).find((k) => leaf(k) === cfg.sort) || cfg.sort;
    hits = [...hits].sort((a, b) => (num(a[key]) ?? Infinity) - (num(b[key]) ?? Infinity));
  }

  const taken = hits.slice(0, cfg.take);
  const ppc = taken.map((r) => perCarat(r, f)).filter((n) => n !== null && n > 0);

  return {
    spec,
    available: hits.length,
    used: ppc.length,
    avg: ppc.length ? ppc.reduce((a, b) => a + b, 0) / ppc.length : null,
    min: ppc.length ? Math.min(...ppc) : null,
    max: ppc.length ? Math.max(...ppc) : null,
    med: ppc.length ? median(ppc) : null,
    stones: taken,
  };
}

const describe = (s) =>
  `${s.carat} ct ${s.label || s.shape} ${s.color} ${s.clarity}`;

/* -------------------------------------------------------------------- *
 * Output
 * -------------------------------------------------------------------- */

function report(results, cfg, f) {
  const cols = ['Spec', 'Matched', 'Used', 'Avg $/ct', 'Median', 'Low', 'High'];
  const rows = results.map((r) => [
    describe(r.spec), String(r.available), String(r.used),
    money(r.avg), money(r.med), money(r.min), money(r.max),
  ]);

  if (cfg.format === 'json') {
    return JSON.stringify(results.map((r) => ({
      spec: describe(r.spec), matched: r.available, averaged: r.used,
      avg_per_carat: r.avg, median_per_carat: r.med,
      low_per_carat: r.min, high_per_carat: r.max,
    })), null, 2);
  }
  if (cfg.format === 'csv') {
    return [cols.join(','), ...rows.map((r) => r.map((c) => (/[",]/.test(c) ? `"${c}"` : c)).join(','))].join('\n');
  }

  const out = [
    `| ${cols.join(' | ')} |`,
    `| ${cols.map(() => '---').join(' | ')} |`,
    ...rows.map((r) => `| ${r.join(' | ')} |`),
  ];

  if (cfg.show) {
    out.push('');
    for (const r of results.filter((x) => x.used)) {
      out.push(`**${describe(r.spec)}** — first ${Math.min(cfg.show, r.stones.length)} of ${r.available}:`);
      for (const s of r.stones.slice(0, cfg.show)) {
        const bits = [
          f.stock && s[f.stock], f.carat && `${s[f.carat]} ct`,
          f.lab && s[f.lab], f.location && s[f.location],
          `${money(perCarat(s, f))}/ct`,
        ].filter(Boolean);
        out.push(`  - ${bits.join(' · ')}`);
      }
      out.push('');
    }
  }
  return out.join('\n');
}

/* -------------------------------------------------------------------- *
 * Main
 * -------------------------------------------------------------------- */

function parseArgs(argv) {
  const cfg = {
    ...DEFAULTS, params: {},
    take: 10, sort: null, caratBand: 0.10,
    lab: 'IGI', location: 'Surat', show: 0, format: 'md', specs: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const next = () => argv[++i];
    switch (argv[i]) {
      case '--specs': cfg.specs = JSON.parse(readFileSync(next(), 'utf8')); break;
      case '--take': cfg.take = Number(next()); break;
      case '--sort': cfg.sort = next(); break;
      case '--carat-band': cfg.caratBand = Number(next()); break;
      case '--lab': cfg.lab = next(); break;
      case '--location': cfg.location = next(); break;
      case '--show': cfg.show = Number(next()); break;
      case '--format': cfg.format = next(); break;
      // passthrough to the fetcher
      case '--base': cfg.base = next(); break;
      case '--endpoint': cfg.endpoint = next(); break;
      case '--auth': cfg.auth = next(); break;
      case '--page-size': cfg.pageSize = Number(next()); break;
      case '--max-pages': cfg.maxPages = Number(next()); break;
      case '--limit': cfg.limit = Number(next()); break;
      case '--param': { const [k, ...v] = next().split('='); cfg.params[k] = v.join('='); break; }
      case '-h': case '--help': cfg.help = true; break;
      default: throw new Error(`Unknown option: ${argv[i]}  (try --help)`);
    }
  }
  return cfg;
}

const HELP = readFileSync(new URL(import.meta.url), 'utf8')
  .split('*/')[0].replace(/^[\s\S]*?\/\*\n/, '').replace(/^ \* ?/gm, '').trim();

async function main() {
  const cfg = parseArgs(process.argv.slice(2));
  if (cfg.help) { console.log(HELP); return; }
  if (!cfg.key) {
    console.error('VDB_API_KEY is not set.\n\n  export VDB_API_KEY=your-key');
    process.exitCode = 1;
    return;
  }
  cfg._auth = authFor(cfg);

  const specs = cfg.specs || SPECS;
  const rows = await fetchAll(cfg, (n) => process.stderr.write(`\rfetched ${n} stones…`));
  process.stderr.write('\r');

  if (!rows.length) {
    console.error('No inventory came back. Run `vdb-to-chat.mjs --probe` to check the endpoint.');
    process.exitCode = 1;
    return;
  }

  const f = resolveFields(rows);
  const missing = ['shape', 'color', 'clarity', 'carat'].filter((k) => !f[k]);
  if (missing.length) {
    console.error(
      `Could not find these fields in the response: ${missing.join(', ')}\n` +
      'Run `vdb-to-chat.mjs --probe` and send me the field list — the names just need adding to ALIASES.'
    );
    process.exitCode = 1;
    return;
  }
  if (!f.perCarat && !f.total) {
    console.error('No price field found. Same fix: --probe, then add the name to ALIASES.');
    process.exitCode = 1;
    return;
  }

  process.stderr.write(
    `${rows.length} stones fetched. Using fields: ` +
    Object.entries(f).filter(([, v]) => v).map(([k, v]) => `${k}=${v}`).join(', ') + '\n' +
    `Filters: lab=${cfg.lab || 'any'}, location=${cfg.location || 'any'}, ` +
    `carat band +${cfg.caratBand}, averaging first ${cfg.take}\n\n`
  );

  const results = specs.map((s) => analyse(rows, s, f, cfg));
  console.log(report(results, cfg, f));

  const empty = results.filter((r) => !r.used);
  if (empty.length) {
    process.stderr.write(
      `\n${empty.length} spec(s) matched nothing: ${empty.map((r) => describe(r.spec)).join('; ')}\n` +
      'Either there is no such stock, or a filter is too tight — try --location "" or --lab "".\n'
    );
  }
}

main().catch((err) => {
  console.error(`\n${redact(err.message, { key: process.env.VDB_API_KEY || '' })}`);
  process.exitCode = 1;
});
