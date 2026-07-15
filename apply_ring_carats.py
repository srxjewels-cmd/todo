#!/usr/bin/env python3
r"""Add a 'Center Carat Weight' option to ring designs that lack carat data.

Reads the pristine catalog + an optional CSV of YOUR real prices
(catalog/ring_carats.csv). Where the CSV gives a price for a (product_id, carat),
that real price is used; otherwise an illustrative PLACEHOLDER derived from the
design's existing base price (edit the CSV to replace). Photos are reused per
colour across carats unless a per-carat photo folder is provided later.

  python apply_ring_carats.py shopdata/variants.json catalog/ring_carats.csv --out enriched.json

The pristine shopdata/variants.json is never modified, so re-running with updated
prices always recomputes correctly from the base.
"""
import json, csv, argparse, os

DEFAULT_TIERS = ["1", "1.5", "2", "2.5", "3"]           # generic centre-stone carat tiers
MULT = {"1": 1.0, "1.5": 1.25, "2": 1.55, "2.5": 1.9, "3": 2.3}  # illustrative placeholder scaling (replace via CSV)
RING_CATS = ("Engagement Rings", "Rings")


def load_csv(path):
    data = {}   # product_id -> {carat -> {price, orig, photo}}
    if not path or not os.path.exists(path):
        return data
    for r in csv.DictReader(open(path, encoding="utf-8")):
        pid = (r.get("product_id") or "").strip()
        car = (r.get("center_carat_weight") or "").strip()
        if not pid or not car:
            continue
        data.setdefault(pid, {})[car] = {
            "price": (r.get("your_price_usd") or "").strip(),
            "orig": (r.get("compare_at_usd_optional") or "").strip(),
            "photo": (r.get("photo_folder_optional") or "").strip(),
        }
    return data


def has_carat(p):
    return any(o["name"] in ("Carat", "Center Carat Weight") for o in p.get("options", []))


def num(s):
    try:
        return float(str(s).replace(",", "").replace("$", ""))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.load(open(a.data, encoding="utf-8"))
    csvd = load_csv(a.csv)
    n = 0
    for p in d:
        if p["cat"] not in RING_CATS or has_carat(p):
            continue
        rows = csvd.get(p["id"], {})
        tiers = sorted([t for t in rows.keys() if num(t) is not None], key=num) if rows else DEFAULT_TIERS
        if not tiers:
            tiers = DEFAULT_TIERS
        opt = {"name": "Center Carat Weight", "type": "select", "values": [{"label": t} for t in tiers]}
        idx = 0
        for i, o in enumerate(p["options"]):
            if o.get("type") == "swatch":
                idx = i + 1
                break
        p["options"].insert(idx, opt)
        newv = []
        for v in p["variants"]:
            base, bo = v.get("usd"), v.get("orig")
            for t in tiers:
                nv = json.loads(json.dumps(v))
                nv["sel"] = dict(v["sel"])
                nv["sel"]["Center Carat Weight"] = t
                row = rows.get(t, {})
                cp, co = num(row.get("price")), num(row.get("orig"))
                if cp is not None:
                    nv["usd"] = int(round(cp))
                elif base is not None:
                    nv["usd"] = int(round(base * MULT.get(t, 1.0)))
                if co is not None:
                    nv["orig"] = int(round(co))
                elif bo:
                    nv["orig"] = int(round(bo * MULT.get(t, 1.0)))
                newv.append(nv)
        p["variants"] = newv
        n += 1
    json.dump(d, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"applied Center Carat Weight to {n} ring designs -> {a.out}")


if __name__ == "__main__":
    main()
