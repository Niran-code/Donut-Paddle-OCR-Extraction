from paddleocr import PaddleOCR
import numpy as np
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.ocr = None

    def _get_model(self):
        if self.ocr is None:
            try:
                logger.info("Initializing PaddleOCR (Lazy Load)...")
                use_gpu = os.environ.get("USE_GPU", "False").lower() == "true"
                # Strict Memory Bounding applied to prevent Exit 247 on low-RAM machines
                self.ocr = PaddleOCR(
                    use_angle_cls=False, 
                    lang=self.lang, 
                    enable_mkldnn=not use_gpu, # MKLDNN is for CPU acceleration
                    use_gpu=use_gpu,
                    show_log=False
                )
                logger.info(f"PaddleOCR ready. (GPU: {use_gpu})")
            except Exception as e:
                logger.error(f"PaddleOCR initialization failed: {e}")
                raise
        return self.ocr

    def extract_text(self, image_path: str) -> Tuple[str, List[str], float]:
        """
        Extracts text from an image.
        Returns: (raw_text_string, list_of_lines, average_confidence)
        """
        model = self._get_model()
        ocr_result = model.ocr(image_path)
        lines = []
        confidences = []

        if isinstance(ocr_result, list) and len(ocr_result) > 0:
            result_obj = ocr_result[0]
            if hasattr(result_obj, 'rec_texts') and result_obj.rec_texts is not None:
                 lines = result_obj.rec_texts
                 confidences = getattr(result_obj, 'rec_scores', [])
            elif isinstance(result_obj, dict) and 'rec_texts' in result_obj:
                 lines = result_obj['rec_texts']
                 confidences = result_obj.get('rec_scores', [])
            elif isinstance(result_obj, list):
                for line in result_obj:
                    if isinstance(line, list) and len(line) >= 2:
                        text_score = line[1]
                        if isinstance(text_score, (tuple, list)) and len(text_score) >= 2:
                            lines.append(text_score[0])
                            confidences.append(text_score[1])
            elif hasattr(result_obj, 'keys'):
                 try:
                     if 'rec_texts' in result_obj:
                         lines = result_obj['rec_texts']
                         confidences = result_obj.get('rec_scores', [])
                 except Exception:
                     pass

        raw_text = " ".join(lines)
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0
        
        return raw_text, lines, avg_confidence
