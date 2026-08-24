# Product Catalogue Generator

Turns a folder of product photos into a clean, printable catalogue —
organised **category-wise**, showing each product's **photo and details**,
with **no prices**.

It was built for the `D:\SHREE RAM` photo folder, but works with any folder.

There are **two ways** to use it — pick whichever suits you:

| | Option A — Browser tool (easiest) | Option B — Python script |
|---|---|---|
| Install anything? | **No** | Yes (Python, once) |
| How | Double-click `catalog_maker.html` | Run a command |
| Best for | Most people | Automating / large batches |

Both keep your photos on your own computer and never show prices.

---

## Option A — Browser tool (no installation) ⭐ recommended

1. Download **`catalog_maker.html`** from this project and save it anywhere
   (e.g. your Desktop).
2. **Double-click it** — it opens in your web browser (Chrome or Edge work
   best). Tip: click **"See a demo"** first to preview the layout.
3. Click **"Choose photo folder…"** and select `D:\SHREE RAM`.
   The catalogue appears instantly, one section per sub-folder.
4. (Optional) Click **"✎ Edit details"** on any item to type its material,
   weight, purity, stone, size, description. Your entries are remembered.
5. Click **"🖨 Save as PDF"** to make a PDF, or **"💾 Download single file"**
   to get one shareable `.html` file (great for WhatsApp / email).

Your photos never leave your computer — the page does everything locally.

---

## Option B — Python script (for automation)

### Why run it on your own PC

Your photos live in `D:\SHREE RAM` on your computer. This tool has to read
those files, so it runs **on your PC**, not in the cloud. It only needs the
one small file `catalog_generator.py` — no internet, nothing to install
beyond Python itself.

---

## One-time setup (5 minutes)

1. Install **Python** (free): https://www.python.org/downloads/
   - On the first install screen, **tick "Add Python to PATH"**, then click
     "Install Now". That checkbox matters.
2. Download `catalog_generator.py` (and, optionally, the
   `Generate_SHREE_RAM_Catalog.bat` launcher) from this project and save
   them somewhere easy, e.g. your Desktop.

---

## Organise your photos by category

Make one **sub-folder per category** inside `D:\SHREE RAM`, and drop the
photos into them:

```
D:\SHREE RAM\
    Rings\
        ring01.jpg
        ring02.jpg
    Necklaces\
        neck01.jpg
    Earrings\
        ear01.jpg
    Bangles\
        bangle01.jpg
```

- Each **folder name becomes a category heading** in the catalogue.
- Photo file names become the product names (e.g. `gold_ring_01.jpg`
  becomes "Gold Ring 01"). You can improve these later — see *Add details*.
- Best photo types: **.jpg** or **.png**. (Phone `.heic` photos may not show —
  convert them to JPG first.)

---

## Make the catalogue

### Easiest: double-click the launcher
If you saved `Generate_SHREE_RAM_Catalog.bat`, put it next to
`catalog_generator.py` and **double-click it**. It builds the catalogue from
`D:\SHREE RAM` automatically.

### Or: run one command
Open **Command Prompt**, then:

```
python "C:\path\to\catalog_generator.py" "D:\SHREE RAM"
```

Either way you get a file called **`SHREE_RAM_Catalog.html`**.
Double-click it to open in any web browser.

### Turn it into a PDF
In the browser: **File > Print > Destination: "Save as PDF" > Save**.
Each category starts on a new page automatically.

---

## Add details (material, weight, purity, etc.)

The first run also creates **`catalog_details_template.csv`** listing every
photo. To add details:

1. Open that CSV in **Excel** (or Google Sheets).
2. Fill in any columns you like — Material, Gross Weight, Net Weight,
   Purity, Stone, Size / Dimensions, Description. Leave blanks where you
   have nothing; empty columns simply won't show.
3. Save the file.
4. Run again, pointing at your details file:

```
python "C:\path\to\catalog_generator.py" "D:\SHREE RAM" --details "catalog_details_template.csv"
```

The catalogue now shows those details under each product.
**There is no price column, on purpose** — and even if you add one, the tool
ignores it.

---

## Options

```
python catalog_generator.py FOLDER [options]

FOLDER                 Folder of photos (default: "D:\SHREE RAM")
-o, --output FILE      Output HTML file name
-t, --title "TEXT"     Cover title (default: the folder name)
-d, --details FILE     CSV of product details to include
-c, --columns N        Products per row (default: 3)
--no-embed             Reference photos instead of embedding them
                       (smaller HTML, but keep it beside the photos)
```

By default every photo is **embedded inside the HTML**, so the single file is
easy to email or share. Large photo sets make a large file; use `--no-embed`
if you'd rather keep the file small and keep it next to the photos.

---

## Quick troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Python isn't on PATH. Re-install and tick "Add Python to PATH". |
| `folder not found` | Check the path and keep it **in quotes**: `"D:\SHREE RAM"`. |
| `No images found` | Put photos inside category sub-folders, then run again. |
| A photo is blank | It's probably `.heic`/`.tiff`. Convert it to `.jpg`. |
