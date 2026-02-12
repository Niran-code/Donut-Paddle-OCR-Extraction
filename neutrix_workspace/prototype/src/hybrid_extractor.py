import re
import os
import cv2
import numpy as np
import base64
from paddleocr import PaddleOCR
from .extract import DonutExtractor
from .regex_cleaner import RegexCleaner
from .utils import print_boxed

class HybridExtractor:
    """
    🚀 Final Hybrid Extractor (Optimized for ID + Marksheet)
    Combines:
      • Donut (semantic layout)
      • PaddleOCR (text extraction)
      • RegexCleaner (field normalization)
      • Face Extraction (OpenCV)
    
    Handles:
      - Aadhaar Card (Specific Format)
      - PAN Card (Specific Format)
      - Marksheets (Specific Format)
    """

    def __init__(self):
        print_boxed("🚀 Initializing Final Hybrid Extractor")
        self.donut = DonutExtractor(model_name="naver-clova-ix/donut-base-finetuned-docvqa")

        try:
            print("⏳ Loading PaddleOCR (English, localized)...")
            # Disable angle classifier to avoid 'cls' argument error
            self.ocr = PaddleOCR(use_angle_cls=False, lang="en", enable_mkldnn=False)
            print("✅ PaddleOCR ready.")
        except Exception as e:
            print(f"❌ PaddleOCR initialization failed: {e}")
            raise

        self.cleaner = RegexCleaner()
        
        # Load Haar Cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def _extract_face(self, image_path: str) -> str:
        """Extracts face from ID card and returns base64 string."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) > 0:
                # Get the largest face
                x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
                
                # Add some padding
                pad_w = int(w * 0.2)
                pad_h = int(h * 0.2)
                h_img, w_img = img.shape[:2]
                
                x1 = max(0, x - pad_w)
                y1 = max(0, y - pad_h)
                x2 = min(w_img, x + w + pad_w)
                y2 = min(h_img, y + h + pad_h)
                
                face_img = img[y1:y2, x1:x2]
                
                _, buffer = cv2.imencode('.jpg', face_img)
                base64_face = base64.b64encode(buffer).decode('utf-8')
                return base64_face
            return None
        except Exception as e:
            print(f"⚠️ Face extraction failed: {e}")
            return None

    def _parse_aadhar(self, text: str, full_text_lines: list) -> dict:
        data = {
            "document_type": "Aadhaar Card",
            "name": None,
            "dob": None,
            "gender": None,
            "aadhaar_number": None
        }
        
        # Aadhaar Number: XXXX XXXX XXXX
        aadhaar_match = re.search(r"\b(\d{4}\s\d{4}\s\d{4})\b", text)
        if aadhaar_match:
            data["aadhaar_number"] = aadhaar_match.group(1)
            
        # DOB: DD/MM/YYYY or YYYY-MM-DD
        dob_match = re.search(r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b", text)
        if dob_match:
            data["dob"] = dob_match.group(1).replace("/", "-") # Standardize to -
            
        # DATE OF YEAR (DOB Alternative)
        if not data["dob"]:
             yob_match = re.search(r"Year of Birth\s*[:\-]?\s*(\d{4})", text, re.IGNORECASE)
             if yob_match:
                 data["dob"] = f"{yob_match.group(1)}-01-01" # Default to Jan 1st if only year
        
        # Gender
        if re.search(r"\b(Male|MALE)\b", text):
            data["gender"] = "Male"
        elif re.search(r"\b(Female|FEMALE)\b", text):
            data["gender"] = "Female"
            
        # Name Strategy: Look for lines that don't contain numbers/keywords, usually near top or after "To"
        # Simple heuristic: Name comes before DOB
        # Cleaning text for name search
        lines = [line.strip() for line in full_text_lines if line.strip()]
        for i, line in enumerate(lines):
             # Skip headers
             if any(x in line.lower() for x in ["govt", "india", "unique", "authorit", "enrollment", "help", "www", "dob", "year", "male", "female"]):
                 continue
             # Check if it looks like a name (Alphabetic, at least 2 words)
             if re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)+$", line) or re.match(r"^[A-Z\s]+$", line):
                 # Avoid capturing "Government of India" etc if missed by filter
                 if len(line.split()) < 2: continue
                 
                 # Heuristic: Name is usually near the DOB line index - 1 or - 2
                 # For now, take the first valid looking name candidate
                 data["name"] = line.title()
                 break
                 
        return data

    def _preprocess_image(self, image_path: str) -> str:
        """Applies preprocessing to improve OCR accuracy."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            # Convert to gray
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply slight Gaussian Blur to remove noise
            # blur = cv2.GaussianBlur(gray, (3, 3), 0)

            # Simple thresholding or adaptive thresholding can help
            # But deep learning OCR usually handles raw well. 
            # Let's try rescaling if image is too small
            height, width = gray.shape
            if width < 1000:
                scale = 1000 / width
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                
            # Save to a temporary path or overwrite? 
            # For safety, let's save to a temp file
            temp_path = image_path.replace(".", "_preprocessed.")
            cv2.imwrite(temp_path, img)
            return temp_path
        except Exception as e:
            print(f"⚠️ Preprocessing failed: {e}")
            return image_path

    def _parse_pan(self, text: str, full_text_lines: list) -> dict:
        data = {
            "document_type": "PAN Card",
            "name": None,
            "father_name": None,
            "dob": None,
            "pan_number": None
        }

        # 1. PAN Number (High Confidence Regex)
        pan_pattern = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
        pan_match = pan_pattern.search(text)
        if pan_match:
            data["pan_number"] = pan_match.group(0)

        # 2. Date of Birth matches (DD/MM/YYYY)
        dob_pattern = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b")
        dob_match = dob_pattern.search(text)
        if dob_match:
            data["dob"] = dob_match.group(1).replace('/', '-')

        # 3. Name & Father's Name Retrieval (Label Based Strategy)
        # OCR often reads "/Name" or "Father's Name" above the value.
        # We also have garbage text at the top. 
        # Strategy: Find "Name" and "Father's Name" lines, take the NEXT line.
        
        lines = [line.strip() for line in full_text_lines if line.strip()]
        
        found_name = False
        found_fname = False
        
        for i, line in enumerate(lines):
            # Check for Father's Name first (since it contains "Name")
            if "Father" in line or "Mother" in line:
                if i + 1 < len(lines):
                    # Validate next line
                    candidate = lines[i+1]
                    if not any(x in candidate for x in ["Number", "Card", "Signature", "Date", "DOB"]):
                         data["father_name"] = candidate
                         found_fname = True
                continue # Skip to next iteration
            
            # Check for Name (but not Father's Name)
            if "Name" in line and "Father" not in line and "Mother" not in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    # Avoid capturing specific keywords
                    if not any(x in candidate for x in ["Number", "Card", "Father", "Mother"]):
                        data["name"] = candidate
                        found_name = True
        
        # 4. Fallback Heuristic (Positional)
        # If labels weren't found, look for capitalized lines that aren't headers
        if not found_name or not found_fname:
             # Basic positional fallback (risky with noise)
             pass 

        return data

    def _extract_marksheet_details(self, text: str, lines: list) -> dict:
        """
        Extracts marksheet details including nested semester data.
        Designed to handle multiple semester blocks and fragmented OCR lines.
        """
        data = {
            "document_type": "Marksheet",
            "university_name": "Unknown",
            "college_name": "Unknown",
            "student_name": "Unknown",
            "university_seat_number": "Unknown",
            "semester": "Unknown",
            "subjects": [],
            "semester_2": [], 
            "semester_1": [], 
            "remarks": {
                "P": "Pass", "F": "Fail", "A": "Absent", "W": "Withheld", "X": "Not Eligible"
            }
        }
        
        # 1. Header Extraction
        uni_match = re.search(r"(Visvesvaraya\s+Technological\s+University|VTU|Anna\s+University)", text, re.IGNORECASE)
        if uni_match:
            data["university_name"] = uni_match.group(1).title()
            
        # 2. Student Details
        usn_match = re.search(r"\b([1-4][A-Z]{2}\d{2}[A-Z]{2,6}\d{1,3})\b", text)
        if usn_match:
            data["university_seat_number"] = usn_match.group(1).upper()
            
        # Name Strategy: Look for "Name" keyword in lines
        for line in lines:
            if "Name" in line and ":" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    clean_name = parts[1].strip()
                    if clean_name and not any(x in clean_name.lower() for x in ["usn", "semester", "result"]):
                        data["student_name"] = clean_name.title()
                        break

        # 3. Semester & Subject Parsing (State Machine)
        # OCR Output is fragmented (Code, Name, Marks are on separate lines)
        # Sequence: Code -> Name -> Int -> Ext -> Tot -> Result
        
        all_semesters_map = {
            "1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [], "8": []
        }
        latest_sem = 0
        current_semester = None
        
        # State Machine Variables
        # states: 'LOOKING_FOR_CODE', 'BUILDING_NAME', 'LOOKING_FOR_MARKS', 'LOOKING_FOR_RESULT'
        state = 'LOOKING_FOR_CODE'
        current_subject = {}
        
        # Buffer for name (since it might be split across lines)
        name_buffer = []
        # Buffer for marks (we need 3 marks: Int, Ext, Tot)
        marks_buffer = []
        
        sem_header_pattern = re.compile(r"Semester\s*[:\-]?\s*(\d+)", re.IGNORECASE)
        code_pattern = re.compile(r"^[A-Z0-9]{5,8}$") # e.g. 17MAT31
        
        for line in lines:
            clean_line = line.strip()
            if not clean_line: continue
            
            # Global Check: Semester Header
            sem_match = sem_header_pattern.search(clean_line)
            if sem_match:
                sem_val = sem_match.group(1)
                current_semester = sem_val
                if int(sem_val) > latest_sem:
                    latest_sem = int(sem_val)
                # Reset state on new semester block
                state = 'LOOKING_FOR_CODE'
                current_subject = {}
                name_buffer = []
                marks_buffer = []
                continue

            # State Machine
            if state == 'LOOKING_FOR_CODE':
                # Check if it looks like a code
                # Ignore headers like "Subject Code"
                if "Code" in clean_line or "Subject" in clean_line: continue
                
                parts = clean_line.split()
                if len(parts) == 1 and code_pattern.match(parts[0]):
                    current_subject['subject_code'] = parts[0]
                    state = 'BUILDING_NAME'
                    name_buffer = []
                elif len(parts) > 1 and code_pattern.match(parts[0]) and parts[-1].isdigit():
                     # Edge case: Code and marks on same line? Unlikely based on logs.
                     pass

            elif state == 'BUILDING_NAME':
                # Accumulate name until we hit a number (which starts marks)
                # But careful: "Mathematics - III" has roman numerals.
                # "26" is definitely a mark.
                
                # Check if this line is purely a number (Mark)
                if clean_line.isdigit():
                    # Found first mark!
                    marks_buffer = [clean_line]
                    current_subject['subject_name'] = " ".join(name_buffer).strip()
                    state = 'LOOKING_FOR_MARKS'
                elif re.match(r"^\d+$", clean_line): # Regex digit check
                     marks_buffer = [clean_line]
                     current_subject['subject_name'] = " ".join(name_buffer).strip()
                     state = 'LOOKING_FOR_MARKS'
                else:
                    # It's part of the name
                    # Filter noise
                    if clean_line.lower() in ["internal", "external", "total", "result", "grade"]:
                        continue
                    name_buffer.append(clean_line)
            
            elif state == 'LOOKING_FOR_MARKS':
                # We need at least 3 marks total (Int, Ext, Tot).
                # But we might encounter noise numbers. Collect all numbers until Result.
                if clean_line.isdigit():
                    marks_buffer.append(clean_line)
                elif clean_line.upper() in ["A", "X", "-"]: # Absent or withheld often in marks col
                     marks_buffer.append("0" if clean_line == "-" else clean_line) # Normalize
                elif re.match(r"^[PFAWX]$", clean_line.upper()) or clean_line.upper() in ["PASS", "FAIL"]:
                    # We might have hit Result early? Or maybe this line IS the result.
                    # Let's check if we have enough marks.
                    # We'll treat this as a transition to RESULT state immediately.
                     state = 'LOOKING_FOR_RESULT'
                     # Don't consume this line yet, let the next block handle it OR handle it here.
                     # Better to handle it here to avoid skipping.
                     res = clean_line.upper()
                     if res in ["PASS", "FAIL"]: res = res[0]
                     
                     if len(marks_buffer) >= 3:
                        current_subject['internal_marks'] = marks_buffer[-3]
                        current_subject['external_marks'] = marks_buffer[-2]
                        current_subject['total'] = marks_buffer[-1]
                        current_subject['result'] = res
                        
                        if current_semester:
                            all_semesters_map.get(current_semester, []).append(current_subject)
                        
                        # Reset
                        state = 'LOOKING_FOR_CODE'
                        current_subject = {}
                        name_buffer = []
                        marks_buffer = []

            elif state == 'LOOKING_FOR_RESULT': # Should rarely reach here if handled above, but for safety
                # Expecting P, F, A, W, X
                res = clean_line.upper()
                if res in ["P", "F", "A", "W", "X", "PASS", "FAIL"]:
                    if res in ["PASS", "FAIL"]: res = res[0]
                    
                    if len(marks_buffer) >= 3:
                        current_subject['internal_marks'] = marks_buffer[-3]
                        current_subject['external_marks'] = marks_buffer[-2]
                        current_subject['total'] = marks_buffer[-1]
                        current_subject['result'] = res
                    
                        if current_semester:
                            all_semesters_map.get(current_semester, []).append(current_subject)
                        
                    # Reset
                    state = 'LOOKING_FOR_CODE'
                    current_subject = {}
                    name_buffer = []
                    marks_buffer = []

        # Populate data structure
        data["semester"] = str(latest_sem) if latest_sem > 0 else "Unknown"
        
        if latest_sem > 0:
            data["subjects"] = all_semesters_map.get(str(latest_sem), [])
            # Backlogs
            if int(latest_sem) > 1:
                sem_2 = all_semesters_map.get("2", [])
                if sem_2: data["semester_2"] = sem_2
                sem_1 = all_semesters_map.get("1", [])
                if sem_1: data["semester_1"] = sem_1

        return data

    def extract_from_image(self, image_path: str) -> dict:
        print(f"\n📸 Processing: {image_path}")
        
        # 1. Face Extraction
        face_base64 = self._extract_face(image_path)
        
        # Preprocessing
        proc_image_path = self._preprocess_image(image_path)
        
        # 2. OCR Extraction
        # Simple call without cls argument
        ocr_result = self.ocr.ocr(proc_image_path)
        
        # Clean up temp file if created
        if proc_image_path != image_path and os.path.exists(proc_image_path):
             try:
                 os.remove(proc_image_path)
             except:
                 pass
        
        print(f"DEBUG: ocr_result type: {type(ocr_result)}")
        lines = []
        confidences = []
        
        # Handle PaddleX OCRResult object
        if isinstance(ocr_result, list) and len(ocr_result) > 0:
            result_obj = ocr_result[0]
            # Check if it's the expected object with rec_texts
            if hasattr(result_obj, 'rec_texts') and result_obj.rec_texts is not None:
                 lines = result_obj.rec_texts
                 confidences = result_obj.rec_scores if hasattr(result_obj, 'rec_scores') else []
            elif isinstance(result_obj, dict) and 'rec_texts' in result_obj:
                 lines = result_obj['rec_texts']
                 confidences = result_obj['rec_scores'] if 'rec_scores' in result_obj else []
            # Fallback to old list of lists structure
            elif isinstance(result_obj, list):
                for line in result_obj:
                    if isinstance(line, list) and len(line) >= 2:
                        text_score = line[1]
                        if isinstance(text_score, (tuple, list)) and len(text_score) >= 2:
                            lines.append(text_score[0])
                            confidences.append(text_score[1])
            # Handle the case where result_obj might be iterable yielding keys (like we saw in logs)
            # but usually accessing attributes/keys is safer if we know them.
            # If the above checks fail, we might need to inspect keys if it behaves like a dict.
            elif hasattr(result_obj, 'keys'): # behaves like dict but didn't pass dict check above?
                 # Try to access as dict
                 try:
                     if 'rec_texts' in result_obj:
                         lines = result_obj['rec_texts']
                         confidences = result_obj['rec_scores'] if 'rec_scores' in result_obj else []
                 except:
                     pass

        raw_text = " ".join(lines)
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0

        
        print(f"DEBUG: OCR Raw Text: {raw_text[:100]}...")
        
        # 3. Detect Document Type & Parse
        base_data = {}
        
        if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", raw_text) or "MALE" in raw_text.upper() or "FEMALE" in raw_text.upper():
             # Potential Aadhaar
             if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", raw_text):
                 base_data = self._parse_aadhar(raw_text, lines)
        
        if not base_data.get("document_type") and re.search(r"[A-Z]{5}\d{4}[A-Z]", raw_text):
             base_data = self._parse_pan(raw_text, lines)
             
        if not base_data.get("document_type") and ( "UNIVERSITY" in raw_text.upper() or "MARKS" in raw_text.upper() or "RESULT" in raw_text.upper()):
             base_data = self._extract_marksheet_details(raw_text, lines)

        # Fallback if detection fails but some ID patterns exist
        if not base_data.get("document_type"):
            base_data["document_type"] = "Unknown"
            
        # Add metadata
        base_data["face_image"] = face_base64
        base_data["ocr_accuracy_score"] = round(avg_confidence * 100, 2)
        
        print("\n✅ Extracted Data:")
        print(base_data)
        return base_data
