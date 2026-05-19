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
            "images": [],
        }

        if image_paths:
            # Add images one by one natively, relying on Word to wrap them
            for img_path in image_paths:
                if os.path.exists(img_path):
                    resized_path = _resize_for_docx(img_path)
                    generated_temp_files.append(resized_path)
                    new_item["images"].append(InlineImage(doc, resized_path, width=Mm(42)))

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