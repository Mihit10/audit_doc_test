import os
import logging

logger = logging.getLogger(__name__)


def _extract_image_index(path: str) -> int:
    """
    Extracts the numeric image index from a filename like:
    obs_<id>_img_<index>.jpg

    Falls back to 0 if parsing fails.
    """
    try:
        base = os.path.basename(path)
        return int(base.split("_img_")[-1].split(".")[0])
    except (ValueError, IndexError):
        return 0


def process(inp: dict) -> dict:
    """
    Simulated processor for the isolated photo-evidence test project.

    Behavior:
    - bypasses SQL/Postgres
    - bypasses LLM
    - normalizes photo metadata into the shape expected by report_generator
    - matches uploaded images to each photo evidence item using the filename prefix
    - keeps the output structure aligned with the DOCX template
    """
    output = {}

    photo_metadata = inp.get("photo_metadata", [])
    photo_evidences_list = []
    photo_dir = inp.get("photo_dir", "")

    if isinstance(photo_metadata, list):
        for photo_dict in photo_metadata:
            if not isinstance(photo_dict, dict):
                continue

            photo_id = str(photo_dict.get("id", "")).strip()
            obs = str(photo_dict.get("observation", "")).strip()

            image_paths = []
            if photo_dir and os.path.exists(photo_dir):
                for filename in os.listdir(photo_dir):
                    if filename.startswith(f"obs_{photo_id}_img_"):
                        image_paths.append(os.path.join(photo_dir, filename))

            image_paths.sort(key=_extract_image_index)

            normalized_photo = {
                "photo_obs": obs,
                "photo_rec": f"SIMULATED RECOMMENDATION for: {obs[:30]}..." if obs else "",
                "image_paths": image_paths,
            }

            photo_evidences_list.append(normalized_photo)

    output["photo_evidence"] = photo_evidences_list
    output["branch_name"] = inp.get("branch_name", "Test_Branch")

    # Hardcoded template-safe fields for the isolated test workspace
    output["overall_risk_level"] = "Low Risk (Hardcoded)"
    output["audit_date"] = "2026-05-20"
    output["audit_engineer_name"] = "Tester"

    return output