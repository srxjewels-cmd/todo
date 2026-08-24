#!/usr/bin/env python3
"""
Product Catalog Generator (photos, category-wise, with details, NO prices).

Point it at a folder of product photos and it builds a clean, printable
HTML catalog. Each sub-folder becomes a category; each image becomes a
product card showing the photo, a product name, an auto-generated code,
and any details you provide -- but never a price.

Typical use (Windows), from a Command Prompt:

    python catalog_generator.py "D:\\SHREE RAM"

That produces "SHREE_RAM_Catalog.html" in the current folder. Open it in
any web browser and use File > Print > "Save as PDF" to get a PDF.

Nothing to install: this uses only the Python standard library.

Folder layout it expects (categories are the sub-folders):

    D:\\SHREE RAM\\
        Rings\\           <- category
            ring01.jpg
            ring02.jpg
        Necklaces\\       <- category
            neck01.jpg
        Earrings\\        <- category
            ear01.jpg

Photos placed directly in the top folder (not in a sub-folder) are grouped
under a single category named after that folder.

Adding details
--------------
Run once and the script writes "catalog_details_template.csv" listing every
photo it found. Open that file in Excel, fill in the columns you want
(Material, Gross Weight, Purity, Stone, Size, Description, ...), save it,
then run again pointing at your details file:

    python catalog_generator.py "D:\\SHREE RAM" --details catalog_details_template.csv

Whatever columns you fill in show up under each product. There is no price
column, on purpose.
"""

import argparse
import base64
import csv
import datetime as _dt
import html
import mimetypes
import os
import re
import sys

# Image types we treat as product photos.
IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg",
}
# Types browsers usually cannot display inline; we warn about these.
NON_WEB_EXTS = {".heic", ".heif", ".tif", ".tiff", ".bmp"}

# Detail columns offered in the template. "Price" is deliberately absent.
DETAIL_COLUMNS = [
    "Product Name",
    "Product Code",
    "Material",
    "Gross Weight",
    "Net Weight",
    "Purity",
    "Stone",
    "Size / Dimensions",
    "Description",
]
# Columns that are structural (used for matching), not shown as a detail line.
_STRUCTURAL = {"Category", "File", "Product Name", "Product Code"}


def natural_key(text):
    """Sort key so 'img2' comes before 'img10'."""
    return [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in re.split(r"(\d+)", str(text))
    ]


def prettify(name):
    """Turn a filename stem into a readable product name."""
    stem = os.path.splitext(name)[0]
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.title() if stem else name


def make_code(category, index):
    """Build a simple product code, e.g. RIN-001."""
    letters = re.sub(r"[^A-Za-z0-9]", "", category).upper()
    prefix = (letters[:3] or "ITM")
    return f"{prefix}-{index:03d}"


def find_categories(root):
    """Return an ordered list of (category_name, [image_paths])."""
    root = os.path.abspath(root)
    categories = []

    # Images sitting directly in the root -> one category named after the root.
    top_images = [
        os.path.join(root, f)
        for f in sorted(os.listdir(root), key=natural_key)
        if os.path.isfile(os.path.join(root, f))
        and os.path.splitext(f)[1].lower() in IMAGE_EXTS
    ]
    if top_images:
        categories.append((os.path.basename(root.rstrip(os.sep)) or "Catalog", top_images))

    # Each sub-folder (recursively flattened per top-level sub-folder) is a category.
    subdirs = sorted(
        (d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))),
        key=natural_key,
    )
    for sub in subdirs:
        subpath = os.path.join(root, sub)
        images = []
        for dirpath, _dirnames, filenames in os.walk(subpath):
            for f in sorted(filenames, key=natural_key):
                if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                    images.append(os.path.join(dirpath, f))
        images.sort(key=lambda p: natural_key(os.path.relpath(p, subpath)))
        if images:
            categories.append((sub, images))

    return categories


def load_details(csv_path):
    """Load the details CSV into {(category_lower, file_lower): {col: value}}."""
    details = {}
    if not csv_path or not os.path.isfile(csv_path):
        return details
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            fname = (row.get("File") or "").strip()
            cat = (row.get("Category") or "").strip()
            if not fname:
                continue
            key = (cat.lower(), os.path.basename(fname).lower())
            details[key] = {k: (v or "").strip() for k, v in row.items()}
            # Also index by filename alone, as a fallback match.
            details.setdefault(("", os.path.basename(fname).lower()), details[key])
    return details


def image_src(path, embed, output_dir):
    """Return an <img src> value: a data URI (embed) or a relative path."""
    if embed:
        mime, _ = mimetypes.guess_type(path)
        mime = mime or "application/octet-stream"
        try:
            with open(path, "rb") as fh:
                data = base64.b64encode(fh.read()).decode("ascii")
            return f"data:{mime};base64,{data}"
        except OSError as exc:
            print(f"  ! could not read {path}: {exc}", file=sys.stderr)
            return ""
    rel = os.path.relpath(path, output_dir)
    return rel.replace(os.sep, "/")


def build_html(title, categories, details, embed, output_dir, columns):
    """Assemble the full catalog HTML document."""
    esc = html.escape
    today = _dt.date.today().strftime("%d %b %Y")
    total = sum(len(imgs) for _, imgs in categories)

    parts = []
    parts.append(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
  :root {{
    --ink:#2b2620; --muted:#7a7166; --line:#e7e0d5;
    --bg:#ffffff; --panel:#faf7f2; --accent:#b8912f;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--bg); color:var(--ink);
    font-family:"Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height:1.5;
  }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:32px 24px 64px; }}
  header.cover {{ text-align:center; padding:48px 16px 24px; border-bottom:2px solid var(--accent); }}
  header.cover .brand {{
    font-family:Georgia,"Times New Roman",serif; font-size:40px; letter-spacing:1px;
    margin:0; color:var(--ink);
  }}
  header.cover .sub {{ color:var(--muted); margin-top:8px; font-size:15px; }}
  header.cover .meta {{ color:var(--muted); margin-top:14px; font-size:13px; }}
  nav.toc {{
    margin:28px auto; padding:18px 22px; background:var(--panel);
    border:1px solid var(--line); border-radius:10px; max-width:640px;
  }}
  nav.toc h2 {{ margin:0 0 10px; font-size:13px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }}
  nav.toc ul {{ margin:0; padding:0; list-style:none; columns:2; column-gap:28px; }}
  nav.toc li {{ margin:4px 0; break-inside:avoid; }}
  nav.toc a {{ color:var(--ink); text-decoration:none; }}
  nav.toc a:hover {{ color:var(--accent); }}
  nav.toc .count {{ color:var(--muted); font-size:12px; }}
  section.category {{ margin-top:44px; }}
  section.category > h2 {{
    font-family:Georgia,"Times New Roman",serif; font-size:26px; margin:0 0 4px;
    padding-bottom:8px; border-bottom:1px solid var(--line);
  }}
  section.category > .cat-meta {{ color:var(--muted); font-size:13px; margin-bottom:18px; }}
  .grid {{
    display:grid; grid-template-columns:repeat({columns}, 1fr); gap:22px;
  }}
  .card {{
    border:1px solid var(--line); border-radius:12px; overflow:hidden;
    background:#fff; display:flex; flex-direction:column; break-inside:avoid;
  }}
  .card .photo {{
    background:var(--panel); aspect-ratio:1/1; display:flex; align-items:center; justify-content:center;
    overflow:hidden;
  }}
  .card .photo img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .card .body {{ padding:12px 14px 16px; }}
  .card .name {{ font-weight:600; font-size:15px; margin:0 0 2px; }}
  .card .code {{ color:var(--accent); font-size:12px; letter-spacing:.06em; margin:0 0 8px; }}
  .card dl {{ margin:0; display:grid; grid-template-columns:auto 1fr; gap:2px 10px; font-size:12.5px; }}
  .card dt {{ color:var(--muted); }}
  .card dd {{ margin:0; }}
  footer.end {{ text-align:center; color:var(--muted); font-size:12px; margin-top:56px; }}
  @media (max-width:820px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} nav.toc ul {{ columns:1; }} }}
  @media (max-width:520px) {{ .grid {{ grid-template-columns:1fr; }} }}
  @media print {{
    nav.toc {{ display:none; }}
    section.category {{ break-before:page; }}
    section.category:first-of-type {{ break-before:auto; }}
    .card {{ box-shadow:none; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ max-width:none; padding:0 8px; }}
  }}
</style>
</head>
<body>
<div class="wrap">
<header class="cover">
  <h1 class="brand">{esc(title)}</h1>
  <div class="sub">Product Catalogue</div>
  <div class="meta">{total} items &middot; {len(categories)} categories &middot; {esc(today)}</div>
</header>
""")

    # Table of contents.
    parts.append('<nav class="toc"><h2>Categories</h2><ul>')
    for cat, imgs in categories:
        anchor = "cat-" + re.sub(r"[^a-z0-9]+", "-", cat.lower()).strip("-")
        parts.append(
            f'<li><a href="#{anchor}">{esc(cat)}</a> '
            f'<span class="count">({len(imgs)})</span></li>'
        )
    parts.append("</ul></nav>")

    # Category sections.
    for cat, imgs in categories:
        anchor = "cat-" + re.sub(r"[^a-z0-9]+", "-", cat.lower()).strip("-")
        parts.append(f'<section class="category" id="{anchor}">')
        parts.append(f"<h2>{esc(cat)}</h2>")
        parts.append(f'<div class="cat-meta">{len(imgs)} item(s)</div>')
        parts.append('<div class="grid">')

        for i, path in enumerate(imgs, start=1):
            fname = os.path.basename(path)
            row = details.get((cat.lower(), fname.lower())) \
                or details.get(("", fname.lower())) or {}

            name = row.get("Product Name") or prettify(fname)
            code = row.get("Product Code") or make_code(cat, i)
            src = image_src(path, embed, output_dir)

            parts.append('<div class="card">')
            if src:
                parts.append(
                    f'<div class="photo"><img src="{esc(src)}" alt="{esc(name)}" loading="lazy"></div>'
                )
            else:
                parts.append('<div class="photo"><span>image unavailable</span></div>')
            parts.append('<div class="body">')
            parts.append(f'<p class="name">{esc(name)}</p>')
            parts.append(f'<p class="code">{esc(code)}</p>')

            # Detail rows: any non-empty, non-structural, non-price column.
            detail_items = []
            for col, val in row.items():
                if not val:
                    continue
                if col in _STRUCTURAL:
                    continue
                if "price" in col.lower() or "amount" in col.lower() or "rate" in col.lower():
                    continue  # never render prices
                detail_items.append((col, val))
            if detail_items:
                parts.append("<dl>")
                for col, val in detail_items:
                    parts.append(f"<dt>{esc(col)}</dt><dd>{esc(val)}</dd>")
                parts.append("</dl>")

            parts.append("</div></div>")  # body, card

        parts.append("</div></section>")

    parts.append(
        '<footer class="end">Prepared with the product catalogue generator &middot; '
        "prices intentionally omitted.</footer>"
    )
    parts.append("</div></body></html>")
    return "\n".join(parts)


def write_details_template(path, categories):
    """Write a CSV listing every photo, ready for the user to fill in."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Category", "File"] + DETAIL_COLUMNS)
        for cat, imgs in categories:
            for i, img in enumerate(imgs, start=1):
                fname = os.path.basename(img)
                writer.writerow(
                    [cat, fname, prettify(fname), make_code(cat, i)]
                    + [""] * (len(DETAIL_COLUMNS) - 2)
                )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a category-wise product photo catalogue (no prices).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "folder", nargs="?", default=r"D:\SHREE RAM",
        help=r'Folder of product photos (default: "D:\SHREE RAM").',
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output HTML file (default: <FolderName>_Catalog.html in the current folder).",
    )
    parser.add_argument(
        "-t", "--title", default=None,
        help="Catalogue title shown on the cover (default: derived from the folder name).",
    )
    parser.add_argument(
        "-d", "--details", default=None,
        help="CSV of product details to merge (Material, Weight, etc.). No price column is used.",
    )
    parser.add_argument(
        "-c", "--columns", type=int, default=3,
        help="Number of product columns in the grid (default: 3).",
    )
    parser.add_argument(
        "--no-embed", action="store_true",
        help="Reference images by relative path instead of embedding them "
             "(smaller file, but keep it alongside the photos).",
    )
    args = parser.parse_args(argv)

    root = args.folder
    if not os.path.isdir(root):
        print(f"ERROR: folder not found: {root}", file=sys.stderr)
        print(
            "Tip: pass the correct path in quotes, e.g.\n"
            '    python catalog_generator.py "D:\\SHREE RAM"',
            file=sys.stderr,
        )
        return 2

    folder_name = os.path.basename(os.path.abspath(root).rstrip(os.sep)) or "Catalog"
    title = args.title or folder_name.replace("_", " ").strip()
    output = args.output or f"{folder_name.replace(' ', '_')}_Catalog.html"
    output_dir = os.path.dirname(os.path.abspath(output))

    print(f"Scanning: {os.path.abspath(root)}")
    categories = find_categories(root)
    if not categories:
        print(
            "No images found. Put your photos in sub-folders "
            "(one sub-folder per category) inside that folder, then run again.",
            file=sys.stderr,
        )
        return 1

    total = sum(len(imgs) for _, imgs in categories)
    print(f"Found {total} photo(s) across {len(categories)} categor(y/ies):")
    for cat, imgs in categories:
        print(f"  - {cat}: {len(imgs)}")

    # Warn about photo types browsers usually can't show.
    non_web = sorted({
        os.path.splitext(os.path.basename(p))[1].lower()
        for _, imgs in categories for p in imgs
        if os.path.splitext(p)[1].lower() in NON_WEB_EXTS
    })
    if non_web:
        print(
            "  ! Note: these formats often will not display in a browser: "
            + ", ".join(non_web)
            + ". Convert them to .jpg or .png for best results."
        )

    details = load_details(args.details)
    if args.details and not details:
        print(f"  ! No usable rows read from details file: {args.details}")

    embed = not args.no_embed
    doc = build_html(title, categories, details, embed, output_dir, max(1, args.columns))
    with open(output, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"\nCatalogue written to: {os.path.abspath(output)}")
    print("Open it in a web browser. To make a PDF: File > Print > Save as PDF.")

    # Offer a details template if the user hasn't supplied one.
    if not args.details:
        template = "catalog_details_template.csv"
        if not os.path.exists(template):
            write_details_template(template, categories)
            print(
                f"\nTo add details (material, weight, purity, description, ...), open\n"
                f"    {os.path.abspath(template)}\n"
                f"fill in the columns, save, then run again with:\n"
                f'    python catalog_generator.py "{root}" --details {template}'
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
