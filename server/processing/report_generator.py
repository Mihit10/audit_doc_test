import os
import logging
from docxtpl import DocxTemplate, InlineImage
from docx import Document
from docx.shared import Mm
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(_BASE_DIR, "..", "templates", "dcb.docx")
REPORTS_ROOT = os.path.join(_BASE_DIR, "..", "reports", "dcb")


def _safe_branch_name(branch_name: str) -> str:
    safe_branch = "".join(
        c if (c.isalnum() or c in (" ", "-", "_")) else "_" for c in branch_name
    ).strip()
    return safe_branch or "unknown"


def _resize_for_docx(img_path: str) -> str:
    """
    Creates a resized JPEG copy next to the original image so InlineImage
    can embed a lighter, DOCX-friendly version.

    Returns the resized image path. If resizing fails, returns the original path.
    """
    base, _ = os.path.splitext(img_path)
    resized_path = f"{base}_resized.jpg"

    try:
        with Image.open(img_path) as im:
            im = ImageOps.exif_transpose(im)

            # Keep it conservative for Word docs and mobile-captured photos
            im.thumbnail((1200, 1200))

            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            else:
                im = im.convert("RGB")

            im.save(resized_path, "JPEG", quality=85, optimize=True)
            return resized_path
    except Exception as e:
        logger.warning("Failed to resize image %s: %s", img_path, e)
        return img_path


def _create_composite_image(image_paths: list, output_path: str) -> str:
    """
    Creates a composite grid image.
    1 image -> original aspect ratio, max width/height
    >1 image -> max 2 columns, N rows, fixed grid size.
    """
    if not image_paths:
        return ""
    try:
        from PIL import Image, ImageOps
        images = []
        for p in image_paths:
            if os.path.exists(p):
                with Image.open(p) as im:
                    im = ImageOps.exif_transpose(im)
                    if im.mode in ("RGBA", "P"):
                        im = im.convert("RGB")
                    else:
                        im = im.convert("RGB")
                    images.append(im.copy())

        if not images:
            return ""

        if len(images) == 1:
            im = images[0]
            im.thumbnail((1200, 1200))
            im.save(output_path, "JPEG", quality=85, optimize=True)
            return output_path

        # 2 or more images -> 2 columns
        cols = 2
        rows = (len(images) + 1) // 2

        # Target cell size for each image in the grid
        cell_w, cell_h = 600, 600
        
        # Grid dimensions
        grid_w = cell_w * cols
        grid_h = cell_h * rows

        composite = Image.new("RGB", (grid_w, grid_h), "white")

        for i, im in enumerate(images):
            # Crop/resize to cell size (center crop)
            im_aspect = im.width / im.height
            cell_aspect = cell_w / cell_h
            if hasattr(Image, 'Resampling'):
                resample_filter = Image.Resampling.LANCZOS
            else:
                resample_filter = Image.LANCZOS

            if im_aspect > cell_aspect:
                new_w = int(im.height * cell_aspect)
                left = (im.width - new_w) // 2
                im = im.crop((left, 0, left + new_w, im.height))
            elif im_aspect < cell_aspect:
                new_h = int(im.width / cell_aspect)
                top = (im.height - new_h) // 2
                im = im.crop((0, top, im.width, top + new_h))
                
            im = im.resize((cell_w, cell_h), resample_filter)
            
            x = (i % cols) * cell_w
            y = (i // cols) * cell_h
            composite.paste(im, (x, y))

        composite.save(output_path, "JPEG", quality=85, optimize=True)
        return output_path
    except Exception as e:
        logger.warning("Failed to create composite image: %s", e)
        if image_paths and os.path.exists(image_paths[0]):
            return _resize_for_docx(image_paths[0])
        return ""


def generate_report(context: dict) -> str:
    template_path = os.path.abspath(TEMPLATE_PATH)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"DOCX template not found: {template_path}")

    context = dict(context)  # work on a copy

    branch_name = str(context.get("branch_name", "Test_Branch")).strip()
    safe_branch = _safe_branch_name(branch_name)

    reports_dir = os.path.abspath(REPORTS_ROOT)
    os.makedirs(reports_dir, exist_ok=True)
    final_path = os.path.join(reports_dir, f"{safe_branch}.docx")

    logger.info("Rendering template: %s", template_path)
    doc = DocxTemplate(template_path)

    original_photo_evidence = context.get("photo_evidence", [])
    flattened_photo_evidence = []
    generated_temp_files = []

    for item in original_photo_evidence:
        if not isinstance(item, dict):
            continue

        image_paths = item.get("image_paths", []) or []
        obs = item.get("photo_obs", "")
        rec = item.get("photo_rec", "")

        new_item = {
            "photo_obs": obs,
            "photo_rec": rec,
            "before_image": "",
            "after_image": "",
        }

        if image_paths:
            import uuid
            composite_filename = f"composite_{uuid.uuid4().hex[:8]}.jpg"
            composite_path = os.path.join(os.path.dirname(image_paths[0]), composite_filename)
            final_img_path = _create_composite_image(image_paths, composite_path)
            
            if final_img_path:
                generated_temp_files.append(final_img_path)
                # Instead of two Mm(45) images side-by-side, use one Mm(90) image
                new_item["before_image"] = InlineImage(doc, final_img_path, width=Mm(90))

        flattened_photo_evidence.append(new_item)

    context["photo_evidence"] = flattened_photo_evidence

    doc.render(context)

    try:
        if os.path.exists(final_path):
            os.remove(final_path)

        doc.save(final_path)
        logger.info("Final report saved: %s", final_path)
    finally:
        # Cleanup temporary photo folder used for this request
        photo_dir = context.get("photo_dir")
        if photo_dir and os.path.exists(photo_dir):
            import shutil
            shutil.rmtree(photo_dir, ignore_errors=True)

        # Cleanup resized temp image copies created for DOCX embedding
        for temp_img in generated_temp_files:
            try:
                if temp_img and os.path.exists(temp_img):
                    os.remove(temp_img)
            except Exception:
                pass

    return final_path