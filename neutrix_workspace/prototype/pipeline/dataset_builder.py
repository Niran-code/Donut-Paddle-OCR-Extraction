import json
import shutil
import os
import uuid
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class DatasetBuilder:
    def __init__(self, base_dir: str = "dataset"):
        self.base_dir = base_dir
        self.images_dir = os.path.join(base_dir, "images")
        self.annotations_dir = os.path.join(base_dir, "annotations")
        self.rejected_dir = os.path.join(base_dir, "rejected")
        
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.annotations_dir, exist_ok=True)
        os.makedirs(self.rejected_dir, exist_ok=True)

    def save_record(self, original_image_path: str, is_valid: bool, data: Dict[str, Any], error_msg: str = ""):
        """
        Saves image and JSON based on validation status.
        Uses a unique identifier.
        """
        doc_type = data.get('document_type', 'Unknown').replace(" ", "_").lower()
        unique_id = f"{doc_type}_{uuid.uuid4().hex[:8]}"
        
        # Determine image extension
        ext = os.path.splitext(original_image_path)[1]
        image_filename = f"{unique_id}{ext}"
        
        if doc_type in ["driving_license", "passport"]:
             target_base_dir = os.path.join(self.base_dir, doc_type)
             target_img_dir = os.path.join(target_base_dir, "images" if is_valid else "rejected")
             target_json_dir = os.path.join(target_base_dir, "annotations" if is_valid else "rejected")
             os.makedirs(target_img_dir, exist_ok=True)
             os.makedirs(target_json_dir, exist_ok=True)
             
             target_img_path = os.path.join(target_img_dir, image_filename)
             target_json_path = os.path.join(target_json_dir, f"{unique_id}.json")
        else:
             target_img_path = os.path.join(self.images_dir if is_valid else self.rejected_dir, image_filename)
             target_json_path = os.path.join(self.rejected_dir if not is_valid else self.annotations_dir, f"{unique_id}.json")
        
        try:
             shutil.copy2(original_image_path, target_img_path)
        except Exception as e:
             logger.error(f"Failed to copy image to dataset: {e}")
             return
             
        # Format the dataset JSON (similar to Donut QA format + metadata)
        record = {
            "image": image_filename,
            "ground_truth": data
        }
        
        if not is_valid:
             record["validation_error"] = error_msg
             
        try:
             with open(target_json_path, 'w', encoding='utf-8') as f:
                 json.dump(record, f, indent=4)
        except Exception as e:
             logger.error(f"Failed to write dataset annotation: {e}")
