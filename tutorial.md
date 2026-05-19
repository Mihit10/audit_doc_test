

# 📚 Detailed Tutorial: From a Messy Single‑Column Photo Table to a Clean, Dynamic Multi‑Image Layout  

## Overview  

The original implementation rendered a **single‑column** table in the DOCX report, forcing a new row for each image and causing the table to expand horizontally. This resulted in:

* Images stacked on top of each other in a single cell.  
* Each observation implicitly started a **new page** because the table row could not split.  
* The Jinja2 template contained `{% tr … %}` and `{% tr endfor %}` tags inside the same row, which `docxtpl` does not recognise, leading to “unknown tag” errors.

The final, production‑ready solution does the following:

1. **Keeps all observations in a single, continuous table** – each observation occupies one table row.  
2. **Shows up to two images per row**, automatically wrapping to a new line (2‑2‑2 layout) when more images are present.  
3. **Uses real InlineImage objects per image** (no composite image).  
4. **Prevents page breaks inside rows** so the table can flow continuously.  
5. **Places the Jinja2 row‑loop tags (`{%tr …%}` and `{%tr endfor%}`) in dedicated rows** – a requirement of `docxtpl`.  

Below is a step‑by‑step guide to replicate this behavior in any similar workflow.

---

## 1️⃣ Prerequisites  

| Tool | Version | Why |
|------|---------|-----|
| **Python** | 3.11+ | Core language |
| **docxtpl** | 0.16.7 | DOCX templating with Jinja2 |
| **python‑docx** | 0.8.11 | Low‑level DOCX manipulation |
| **Pillow** | 10.2.0 | Image resizing / format handling |

Install the dependencies inside your virtual environment:

```bash
python -m venv venv
.\venv\Scripts\activate
pip install docxtpl python-docx Pillow
```

---

## 2️⃣ DOCX TEMPLATE – Proper Row Loop Placement  

`docxtpl` only recognises **full‑row loops** (`{%tr …%}` / `{%tr endfor%}`) when they occupy **their own rows**.  

### Steps  

1. **Open the template** (`templates/dcb.docx`) in Microsoft Word.  
2. **Insert two empty rows** *above* the data row that will hold the photo evidence.  
   * Row 1 → contains `{%tr for item in photo_evidence %}` as the only content.  
   * Row N → contains `{%tr endfor %}` as the only content.  
3. **Leave the “data” row** (the one that displays the images and text) **without any loop tags** – it should only contain the placeholders:  

   | Column 1 | Column 2 | Column 3 |
   |----------|----------|----------|
   | `{{item.before_image}}`<br>`{{item.after_image}}` | `{{item.photo_obs}}` | `{{item.photo_rec}}` |

4. **Remove any `cantSplit` property** from the table rows (Word → Table → Properties → Row → *uncheck* “Allow row to break across pages”). This lets the table flow without forced page breaks.  

5. **Save** the template.

> **Tip:** You can verify that the rows are correctly placed by dumping the XML:

```python
from docxtpl import DocxTemplate
tpl = DocxTemplate('templates/dcb.docx')
xml = tpl.patch_xml(tpl.get_xml())
print(xml)   # Look for {%tr …%} surrounding the row definitions
```

---

## 3️⃣ Backend – Image Handling  

### 3.1 Remove Composite‑Image Logic  

The original code built a single composite JPEG (max 2 cols) and inserted it as one large image. Replace that with **individual images**.

```python
# Remove the entire _create_composite_image function.
# Keep only the _resize_for_docx helper (it creates a lightweight JPEG copy).
```

### 3.2 Update `generate_report`  

Key changes (see `server/processing/report_generator.py`):

| Old Code | New Code |
|----------|----------|
| `new_item = {"photo_obs":…, "photo_rec":…, "before_image": "", "after_image": ""}` | `new_item = {"photo_obs":…, "photo_rec":…, "images": []}` |
| Composite image creation, `new_item["before_image"] = InlineImage(..., width=Mm(90))` | Loop through each `img_path` → resize via `_resize_for_docx` → `new_item["images"].append(InlineImage(doc, resized_path, width=Mm(42)))` |
| Context key `photo_evidence` held a list of dicts with `before_image`/`after_image`. | Context key `photo_evidence` now holds a list of dicts with an **`images` list** (array of `InlineImage` objects). |

**Why `Mm(42)`?**  
* Fits two images side‑by‑side (≈ 84 mm total) inside a standard A4 page width, leaving margins.  
* Word will automatically wrap a third image onto the next line (2‑2‑2 layout).

### 3.3 Template Adjustments  

Update the data row to iterate over the new `images` list:

```xml
{%tr for item in photo_evidence %}
    <w:tc> <!-- Images cell -->
        {% for img in item.images %}{{ img }} {% endfor %}
    </w:tc>
    <w:tc>{{ item.photo_obs }}</w:tc>
    <w:tc>{{ item.photo_rec }}</w:tc>
{%tr endfor %}
```

*The `{% for img in item.images %}` loop is **inside the same cell** and will render each image sequentially. Word takes care of line‑breaks after every second image.*

---

## 4️⃣ Prevent Page Breaks Inside Rows  

Even with the `cantSplit` flag removed from the template, you should also ensure the generated rows have it cleared programmatically (helps for templates edited outside Word):

```python
from docx.oxml.ns import qn

for table in doc.tables:
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = tr_pr.find(qn('w:cantSplit'))
        if cant_split is not None:
            tr_pr.remove(cant_split)
```

*(The snippet is included in the tutorial script that patches the template after loading.)*

---

## 5️⃣ Cleaning Up Temporary Files  

All resized images are stored temporarily in the same folder as the originals. After the DOCX is saved, the backend deletes them:

```python
for tmp in generated_temp_files:
    if os.path.exists(tmp):
        os.remove(tmp)
```

That logic already existed; the only change is that **each original image now generates its own temporary resized copy**.

---

## 6️⃣ End‑to‑End Flow Recap  

1. **Frontend**: Upload images → store in IndexedDB → send `photo_evidence` JSON (including `image_paths`).  
2. **Server Processor** (`processor.py`) → normalises the payload into the shape required by the report.  
3. **Report Generator** (`report_generator.py`)  
   * Resizes each image (`_resize_for_docx`).  
   * Wraps each `InlineImage` in the `images` list of the observation dict.  
   * Supplies `photo_evidence` to the template.  
4. **DOCX Rendering** (`docxtpl`)  
   * Reads `templates/dcb.docx`.  
   * Finds the row‑loop tags (`{%tr …%}`) placed in dedicated rows.  
   * Renders each observation row, inserting the image list.  
5. **Result**: A **single, continuous table** where each observation gets one row; up to two images appear per line, automatically flowing to the next line when more images are present. No unwanted page breaks.

---

## 7️⃣ How to Re‑use This Pattern in Your Own Projects  

| Step | Action |
|------|--------|
| **A** | Create a DOCX template with a table. Insert **two empty rows**: one with `{%tr for item in YOUR_LOOP %}` and one with `{%tr endfor %}`. |
| **B** | In the data row, reference `{{ item.images }}` (or any collection) with a **nested `for` loop** inside the cell. |
| **C** | In Python, for each observation, build a list of `InlineImage` objects (resize first). |
| **D** | Pass the list of observation dicts to `doc.render(context)`. |
| **E** | Ensure rows have `cantSplit` cleared if you edited the template outside Word. |
| **F** | Save the generated DOCX and clean temporary images. |

> **Tip:** If you need a *different max‑columns* layout, simply adjust the image width (`Mm(42)`) and/or add CSS‑like logic in Jinja (`{% if loop.index is odd %}<w:br/>%}`) to force line breaks after every N images.

---

## 8️⃣ Full Example – Minimal Working Code  

```python
# server/processing/report_generator.py (excerpt)

import os, logging, uuid
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

def _resize_for_docx(img_path: str) -> str:
    base, _ = os.path.splitext(img_path)
    out = f"{base}_resized.jpg"
    try:
        with Image.open(img_path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((1200, 1200))
            im.save(out, "JPEG", quality=85, optimize=True)
        return out
    except Exception as e:
        logger.warning("Resize failed for %s: %s", img_path, e)
        return img_path

def generate_report(context: dict) -> str:
    tpl_path = os.path.abspath("templates/dcb.docx")
    doc = DocxTemplate(tpl_path)

    flattened = []
    temp_files = []

    for obs in context.get("photo_evidence", []):
        if not isinstance(obs, dict):
            continue
        images = []
        for p in obs.get("image_paths", []):
            if os.path.exists(p):
                resized = _resize_for_docx(p)
                temp_files.append(resized)
                images.append(InlineImage(doc, resized, width=Mm(42)))
        flattened.append({
            "photo_obs": obs.get("photo_obs", ""),
            "photo_rec": obs.get("photo_rec", ""),
            "images": images,
        })

    context["photo_evidence"] = flattened
    doc.render(context)
    out_path = os.path.join("reports", "dcb", "final.docx")
    doc.save(out_path)

    # cleanup
    for f in temp_files:
        try: os.remove(f)
        except: pass

    return out_path
```

---

## 9️⃣ Testing the Result  

Run the Flask endpoint (or the equivalent test script) and open the generated DOCX. You should see:

* **One table row per observation** (no extra blank rows).  
* **Two images per line**, automatically wrapping to a new line for the third/fourth image.  
* **No page breaks** splitting rows.  

If you see any extra blank rows, double‑check that the `{%tr …%}` tags are on their own rows in the template.

---

## 📌 Summary  

- **Template changes**: Dedicated `{%tr …%}` rows, removed `cantSplit`.  
- **Backend changes**: Dropped composite image generation, added per‑image `InlineImage` list, updated context keys.  
- **Result**: A clean, continuous table with a flexible 2‑image‑per‑line layout that scales to any number of photos without forcing new pages.

Feel free to copy the snippets, adjust image widths, or adapt the table structure to suit other report types. Happy templating!