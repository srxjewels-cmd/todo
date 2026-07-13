#!/usr/bin/env python3
r"""Organize scraped ring folders.

Takes a folder of scraped product folders (e.g. "1. Some Ring", "2. ...")
and reorganizes it into:

    <root>\Engagement Ring\ 1. <cheapest> ... N. <priciest>
    <root>\Others\         1. <cheapest> ... N. <priciest>

For every product it:
  * classifies it as an engagement ring or "other" (by keywords in the
    product name / details text - edit ENGAGEMENT_KEYWORDS below to tune),
  * sorts each group by price low -> high and renumbers the folders 1..N,
  * renames that product's details text file to the product's price
    (e.g. details.txt -> "$1,150.00.txt"), leaving photos/info.txt as-is.

Usage:
    python organize_rings.py "D:\quine p\prd\Rings"
    python organize_rings.py "D:\quine p\prd\Rings" --yes   # skip confirmation

Or double-click Organize_Rings.bat (defaults to D:\quine p\prd\Rings, or drag
a folder onto it). Nothing is changed until you confirm.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# A product goes to "Engagement Ring" if any of these words appears in its
# name or details text (case-insensitive); otherwise it goes to "Others".
# Add or remove words here to change how things are split.
ENGAGEMENT_KEYWORDS = [
    "engagement", "bridal", "solitaire", "halo",
    "three stone", "three-stone", "trilogy",
]

CATEGORY_ENGAGEMENT = "Engagement Ring"
CATEGORY_OTHER = "Others"
SKIP_TXT = {"info.txt", "photo_urls.txt", "_summary.txt"}


def read_info(folder):
    name, price_str = "", ""
    info = folder / "info.txt"
    if info.exists():
        for line in info.read_text(encoding="utf-8", errors="ignore").splitlines():
            low = line.lower()
            if low.startswith("product name:"):
                name = line.split(":", 1)[1].strip()
            elif low.startswith("price:"):
                price_str = line.split(":", 1)[1].strip()
    return name, price_str


def parse_price(s):
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def strip_leading_number(name):
    return re.sub(r"^\s*\d+\s*[.\-)]\s*", "", name).strip()


def sanitize(s, max_len=70):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", s or "")
    s = re.sub(r"\s+", " ", s).strip().strip(".").strip()
    return s[:max_len].rstrip(" .")


def details_txt_file(folder):
    for f in sorted(folder.glob("*.txt")):
        if f.name.lower() not in SKIP_TXT:
            return f
    return None


def read_details_text(folder):
    f = details_txt_file(folder)
    if f:
        try:
            return f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    return ""


def is_engagement(name, details_text):
    hay = f"{name} {details_text}".lower()
    return any(k in hay for k in ENGAGEMENT_KEYWORDS)


def price_filename(price, price_str):
    if price is not None:
        label = f"${price:,.2f}"
    elif price_str:
        label = price_str
    else:
        return "details"          # unknown price -> keep a sensible name
    return sanitize(label, 50) or "details"


def collect_products(root):
    skip = {CATEGORY_ENGAGEMENT.lower(), CATEGORY_OTHER.lower()}
    products = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.lower() in skip:
            continue
        # Only treat folders that look like scraped products.
        if not (d / "info.txt").exists() and not details_txt_file(d) \
                and not list(d.glob("photo_*.jpg")):
            continue
        name, price_str = read_info(d)
        clean = strip_leading_number(d.name) or name or d.name
        details = read_details_text(d)
        products.append({
            "path": d,
            "clean": clean,
            "price": parse_price(price_str),
            "price_str": price_str,
            "eng": is_engagement(name or clean, details),
        })
    return products


def plan(products):
    eng = [p for p in products if p["eng"]]
    oth = [p for p in products if not p["eng"]]

    def key(p):
        return (p["price"] is None, p["price"] or 0.0, p["clean"].lower())

    eng.sort(key=key)
    oth.sort(key=key)
    return eng, oth


def print_plan(eng, oth):
    for cat, items in ((CATEGORY_ENGAGEMENT, eng), (CATEGORY_OTHER, oth)):
        print(f"\n{cat} ({len(items)}):")
        for i, p in enumerate(items, 1):
            price = f"${p['price']:,.2f}" if p["price"] is not None else "(no price)"
            print(f"  {i:>2}. {price:>12}  {p['clean'][:55]}")


def apply(root, eng, oth):
    report = ["old_folder\tnew_location\tprice_file"]
    for cat, items in ((CATEGORY_ENGAGEMENT, eng), (CATEGORY_OTHER, oth)):
        cat_dir = root / cat
        cat_dir.mkdir(exist_ok=True)
        for i, p in enumerate(items, 1):
            new_name = sanitize(f"{i}. {p['clean']}") or f"{i}. ring"
            dest = cat_dir / new_name
            if dest.exists() and dest.resolve() != p["path"].resolve():
                new_name = f"{i}. {sanitize(p['clean'])} [{p['path'].name}]"
                dest = cat_dir / new_name
            if p["path"].resolve() != dest.resolve():
                shutil.move(str(p["path"]), str(dest))
            # rename the details text file to the price
            pf = price_filename(p["price"], p["price_str"])
            src_txt = details_txt_file(dest)
            price_file = ""
            if src_txt is not None:
                target = dest / f"{pf}.txt"
                if src_txt.resolve() != target.resolve():
                    if target.exists():
                        target.unlink()
                    src_txt.rename(target)
                price_file = target.name
            report.append(f"{p['path'].name}\t{cat}/{dest.name}\t{price_file}")
    (root / "_organized_report.tsv").write_text("\n".join(report) + "\n",
                                                encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default=r"D:\quine p\prd\Rings")
    ap.add_argument("--yes", action="store_true", help="apply without confirmation")
    args = ap.parse_args(argv)

    root = Path(args.folder)
    if not root.is_dir():
        print(f"Folder not found:\n  {root}")
        return 1
    print(f"Scanning: {root}")
    products = collect_products(root)
    if not products:
        print("No product folders found here (expected subfolders with "
              "info.txt / photos / a details .txt).")
        return 1

    eng, oth = plan(products)
    print(f"\nFound {len(products)} rings -> {len(eng)} engagement, {len(oth)} others.")
    print_plan(eng, oth)
    print("\nEach folder will move into its category, be renumbered by price "
          "(low->high),\nand its details text file renamed to the price.")

    if not args.yes:
        try:
            ans = input("\nApply these changes? Type Y and press Enter: ").strip().lower()
        except EOFError:
            ans = "n"
        if ans not in ("y", "yes"):
            print("Cancelled - nothing was changed.")
            return 0

    apply(root, eng, oth)
    print(f"\nDone. Organized into '{CATEGORY_ENGAGEMENT}' and '{CATEGORY_OTHER}'.")
    print(f"A log of what moved where is in: {root / '_organized_report.tsv'}")
    return 0


if __name__ == "__main__":
    rc = main()
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass
    sys.exit(rc)
