import cv2
import base64
import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class Preprocessor:
    def __init__(self, face_cascade_path: str = "models/haarcascade_frontalface_default.xml"):
        if os.path.exists(face_cascade_path):
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            logger.info("Loaded Haar Cascade for face detection.")
        else:
            self.face_cascade = None
            logger.warning(f"Haar Cascade not found at {face_cascade_path}")

    def extract_face(self, image_path: str) -> Optional[str]:
        """Extracts face from ID card and returns base64 string."""
        if not self.face_cascade:
            return None

        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) > 0:
                x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
                
                pad_w = int(w * 0.2)
                pad_h = int(h * 0.2)
                h_img, w_img = img.shape[:2]
                
                x1 = max(0, x - pad_w)
                y1 = max(0, y - pad_h)
                x2 = min(w_img, x + w + pad_w)
                y2 = min(h_img, y + h + pad_h)
                
                face_img = img[y1:y2, x1:x2]
                _, buffer = cv2.imencode('.jpg', face_img)
                return base64.b64encode(buffer).decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Face extraction failed: {e}")
            return None

    def preprocess_image(self, image_path: str) -> str:
        """Applies preprocessing to improve OCR accuracy."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Add a white border so edge-touching text is easily bounded by PaddleOCR
            border_size = 50
            padded = cv2.copyMakeBorder(
                gray, 
                border_size, border_size, border_size, border_size, 
                cv2.BORDER_CONSTANT, 
                value=[255, 255, 255]
            )
            
            # Add a white border so edge-touching text is easily bounded by PaddleOCR
            border_size = 50
            padded = cv2.copyMakeBorder(
                gray, 
                border_size, border_size, border_size, border_size, 
                cv2.BORDER_CONSTANT, 
                value=[255, 255, 255]
            )
            
            # Very slight resize to normalize resolution without distorting text
            height, width = padded.shape
            scale = 1800 / width
            resized = cv2.resize(padded, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            
            temp_path = image_path.replace(".", "_preprocessed.")
            cv2.imwrite(temp_path, resized)
            return temp_path
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return image_path
