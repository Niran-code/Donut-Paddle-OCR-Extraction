import os
import logging
from typing import Dict, Any
from .preprocess import Preprocessor
from .ocr_engine import OCREngine
from .donut_engine import DonutEngine
from .cleaner import RegexCleaner
from .validator import Validator
from .dataset_builder import DatasetBuilder

logger = logging.getLogger(__name__)

class HybridExtractorPipeline:
    def __init__(self, use_donut: bool = False):
        logger.info("Initializing Hybrid Extractor Pipeline...")
        self.preprocessor = Preprocessor()
        self.ocr_engine = OCREngine()
        self.cleaner = RegexCleaner()
        self.dataset_builder = DatasetBuilder()
        
        self.use_donut = use_donut
        if self.use_donut:
             self.donut_engine = DonutEngine()
        else:
             self.donut_engine = None

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Main pipeline execution flow.
        Input -> Preprocess -> OCR -> Regex/Donut -> Validate -> Dataset Build -> Result
        """
        logger.info(f"Processing: {file_path}")
        
        # 1. Preprocess & Face Extraction
        face_b64 = self.preprocessor.extract_face(file_path)
        proc_image_path = self.preprocessor.preprocess_image(file_path)
        
        # 2. OCR Extraction
        raw_text, lines, avg_confidence = self.ocr_engine.extract_text(proc_image_path)
        logger.debug(f"OCR Raw Text extracted length: {len(raw_text)}")
        
        # Cleanup preprocessed image if temporary
        if proc_image_path != file_path and os.path.exists(proc_image_path):
             try:
                 os.remove(proc_image_path)
             except Exception:
                 pass
                 
        # 3. Clean and parse using Regex Heuristics
        extracted_data = self.cleaner.extract_document(raw_text, lines)
        
        # Additive Enhancement: Route to new processors if it's not an existing doc type
        if extracted_data.get("document_type") == "Unknown":
            import re
            from .driving_license_processor import process_driving_license
            from .passport_processor import process_passport
            
            text_lower = raw_text.lower()
            
            def is_driving_license(text: str) -> bool:
                patterns = [
                    r"dl\sno",
                    r"driving\slicence",
                    r"driving\slicense",
                    r"valid\sthroughout\sindia",
                    r"\bmcwg\b",
                    r"\blmv\b",
                    r"\bform\s7\b"
                ]
                for pattern in patterns:
                    if re.search(pattern, text):
                        return True
                return False

            def is_passport(text: str) -> bool:
                patterns = [
                    r"passport",
                    r"p<ind",
                    r"republic\s*of\s*india",
                    r"/nationality",
                    r"/placeofssue",
                    r"x[0-9]{7}",
                    r"\bp<"
                ]
                text_clean = text.replace(" ", "")
                for pattern in patterns:
                    if re.search(pattern, text) or re.search(pattern, text_clean):
                        return True
                return False

            if is_driving_license(text_lower):
                extracted_data = process_driving_license(raw_text, lines)
            elif is_passport(text_lower):
                extracted_data = process_passport(raw_text, lines)
        
        # 4. Fallback to Donut if primary extraction failed
        # If document is still unknown, try Donut
        if self.use_donut and extracted_data.get("document_type") == "Unknown":
            logger.info("Regex extraction returned Unknown, falling back to Donut...")
            donut_data = self.donut_engine.process_image(file_path)
            
            # Merge logic - basic override if donut finds a type
            if donut_data and isinstance(donut_data, dict):
                 if "document_type" in donut_data:
                     for k, v in donut_data.items():
                         if k not in extracted_data or not extracted_data[k]:
                             extracted_data[k] = v
        
        # Add metadata
        if extracted_data.get("document_type") == "Unknown" and raw_text:
            extracted_data["raw_text"] = raw_text

        extracted_data["face_image"] = face_b64
        extracted_data["ocr_accuracy_score"] = round(avg_confidence * 100, 2)
        
        # 5. Pydantic Validation
        is_valid, final_data, error_msg = Validator.validate_document(extracted_data)
        
        # 6. Dataset Building
        self.dataset_builder.save_record(
            original_image_path=file_path,
            is_valid=is_valid,
            data=final_data,
            error_msg=error_msg
        )
        
        return final_data
