# Prompt for Claude Code (run on your own PC) — build the catalogue PDF

Run Claude Code on your Windows computer (it can see `D:\SHREE RAM`, unlike the
cloud), then **paste the prompt below**. It will build the finished PDF for you.

## How to use it
1. Open **Command Prompt** (or Windows Terminal).
2. Type `claude` and press Enter to start Claude Code.
   (If you don't have it yet, install "Claude Code" first, then try again.)
3. **Paste the whole prompt below** and press Enter. Let it install what it needs,
   run, and produce the PDF at `D:\SHREE RAM\SHREE_RAM_Catalogue.pdf`.

---

## The prompt (copy everything between the lines)

```
I have a folder of jewellery product photos at D:\SHREE RAM. Inside it, the
photos are organised into sub-folders where EACH SUB-FOLDER IS A PRODUCT
CATEGORY (for example: Rings, Necklaces, Earrings, Bangles).

Build a complete, print-ready PDF product catalogue from these photos and save
it as D:\SHREE RAM\SHREE_RAM_Catalogue.pdf.

Requirements:
- Organise the catalogue BY CATEGORY: one section per sub-folder, sorted in
  natural alphabetical order, each with the category name as a heading. Start
  each new category on a new page.
- For EVERY photo show three things: the product photo, a PRODUCT NAME derived
  from the file name (replace _ and - with spaces, Title Case), and an
  auto-generated PRODUCT CODE = first 3 letters of the category + a running
  number, e.g. RIN-001, NEC-002.
- DO NOT SHOW ANY PRICES anywhere in the catalogue.
- Add a COVER PAGE at the very top: title "SHREE RAM", subtitle
  "Product Catalogue", today's date, and the total number of items and
  categories.
- Lay products out in a neat grid, about 3 per row, A4 size, with clean margins
  so it prints nicely. Keep image boxes a consistent size.
- Include ALL images found in every sub-folder. Handle .jpg, .jpeg, .png, .webp.
  If you find .heic or .heif photos, convert them to JPG first so they appear.
- Resize each photo so its longest side is about 1000-1200 px (never upscale
  small ones) so the final PDF is a reasonable file size.
- Sort categories, and photos within each category, in NATURAL order (image2
  before image10).
- OPTIONAL: if a file D:\SHREE RAM\details.csv exists with columns like
  Category, File, Material, Gross Weight, Net Weight, Purity, Stone, Size,
  Description, merge those details under the matching product (match by the File
  name). Never include a price column even if one is present.

Please install whatever you need (for example Python with Pillow and a PDF
library such as fpdf2 or reportlab, plus pillow-heif if there are HEIC files),
write the script, RUN it, and tell me the final PDF path and its page count. If
any images fail to load, skip them and list which ones at the end.
```

---

### Tips
- Best photo types are `.jpg` / `.png`. HEIC phone photos are handled (converted
  automatically) but add a little time.
- Want nicer product names or details (material, weight, purity)? Create a
  `details.csv` in `D:\SHREE RAM` with a `File` column plus the detail columns —
  the prompt already tells Claude to merge it in. (No price column, ever.)
- If you'd like a different look (2 per row, a logo on the cover, larger photos),
  just add that sentence to the prompt before you send it.
