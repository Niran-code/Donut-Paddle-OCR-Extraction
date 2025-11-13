import re
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

    Handles:
      - Aadhaar / PAN / Driving License
      - University Mark Sheets (multi-semester, UG/PG)
    """

    def __init__(self):
        print_boxed("🚀 Initializing Final Hybrid Extractor (Optimized for Marksheet 90%+)")
        self.donut = DonutExtractor(model_name="naver-clova-ix/donut-base-finetuned-docvqa")

        try:
            print("⏳ Loading PaddleOCR (English only, cached locally)...")
            self.ocr = PaddleOCR(use_angle_cls=True, lang="en")
            print("✅ PaddleOCR (English) ready.")
        except Exception as e:
            print(f"❌ PaddleOCR initialization failed: {e}")
            raise

        self.cleaner = RegexCleaner()

    # -------------------------------------------------------------------------
    def _extract_fields_from_text(self, text: str) -> dict:
        """Extracts base identity fields from OCR text."""
        data = {}

        aadhaar = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text)
        if aadhaar:
            data["aadhaar_number"] = " ".join(aadhaar.group(1).split())

        pan = re.search(r"\b([A-Z]{5}\d{4}[A-Z])\b", text)
        if pan:
            data["pan_number"] = pan.group(1)

        dl = re.search(r"\b([A-Z]{2}\d{2}[-\s]?\d{4,7})\b", text)
        if dl:
            data["dl_number"] = dl.group(1).replace(" ", "")

        dob = re.search(r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b", text)
        if dob:
            data["dob"] = dob.group(1).replace(".", "/")

        name = re.search(r"(?:Name|NAME|नाम)[:\s]*([A-Z][A-Za-z\s]+)", text)
        if name:
            data["name"] = name.group(1).title().strip()

        return data

    # -------------------------------------------------------------------------
    def _extract_marksheet_details(self, text: str) -> dict:
        """🎓 Advanced parser for university mark sheets (UG, PG, MBA)."""
        marksheet_data = {}
        text = re.sub(r"\s+", " ", text).strip()

        # --- University Name ---
        uni_match = re.search(
            r"(Visvesvaraya\s+Technological\s+University|VTU|Anna\s+University|Osmania\s+University|JNTU|Technological\s+University|University\s+of\s+[A-Za-z]+)",
            text, re.IGNORECASE
        )
        if uni_match:
            marksheet_data["university_name"] = uni_match.group(0).strip().title()

        # --- College / Institute ---
        college_match = re.search(r"\b(Institute|College|University|VTU)\b", text, re.IGNORECASE)
        marksheet_data["college_name"] = (
            college_match.group(0).strip().title() if college_match else "VTU"
        )

        # --- University Seat Number (extended for MBA, MTech, BE) ---
        usn = re.search(r"\b([1-4][A-Z]{2}\d{2}[A-Z]{2,6}\d{1,3})\b", text)
        if not usn:
            usn = re.search(r"USN\s*[:\-]?\s*([A-Z0-9]+)", text, re.IGNORECASE)
        if usn:
            marksheet_data["university_seat_number"] = usn.group(1).strip().upper()

        # --- Student Name (stop before semester or subject) ---
        student = re.search(
            r"(?:Student\s*Name\s*[:\-]?\s*)([A-Z][A-Za-z\s]+?)(?=\s*(?:Semester|Subject|Code|Internal|External|Result|Marks|$))",
            text,
        )
        if student:
            name = student.group(1).strip().title()
            marksheet_data["student_name"] = name

        # --- Semester ---
        sem_match = re.search(r"Semester\s*[:\-]?\s*(\d{1,2})\b", text, re.IGNORECASE)
        marksheet_data["semester"] = sem_match.group(1) if sem_match else "Unknown"

        # --- Subject Extraction Patterns ---
        subject_patterns = [
            re.compile(
                r"([A-Z0-9]{2,6}[A-Z]{1,3}\d{1,4})\s+([A-Za-z&\.\-\,\s]+?)\s+(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s+([PFWA])",
                re.IGNORECASE,
            ),
            re.compile(
                r"([A-Z0-9]{2,6}[A-Z]{1,3}\d{1,4})\s+([A-Za-z&\.\-\,]+(?:\s+[A-Za-z&\.\-\,]+)*)\s+(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s*([PFWA])",
                re.IGNORECASE,
            ),
        ]

        subjects = []
        for pattern in subject_patterns:
            for match in pattern.finditer(text):
                subject_name = re.sub(r"[^A-Za-z&,\.\-\s]", "", match.group(2)).strip().title()
                subject_name = re.sub(r"\s{2,}", " ", subject_name)
                subjects.append({
                    "subject_code": match.group(1).strip(),
                    "subject_name": subject_name,
                    "internal_marks": match.group(3),
                    "external_marks": match.group(4),
                    "total": match.group(5),
                    "result": match.group(6).upper(),
                })

        # --- Fallback Parser (for noisy data) ---
        if not subjects or len(subjects) < 5:
            for line in re.split(r"[\n/]", text):
                tokens = line.strip().split()
                if len(tokens) < 6:
                    continue
                if re.match(r"^[A-Z0-9]{2,6}[A-Z]{1,3}\d{1,4}$", tokens[0]):
                    try:
                        code = tokens[0]
                        result = tokens[-1].upper()
                        total = tokens[-2]
                        external = tokens[-3]
                        internal = tokens[-4]
                        name = " ".join(tokens[1:-4])
                        subjects.append({
                            "subject_code": code,
                            "subject_name": name.title(),
                            "internal_marks": internal,
                            "external_marks": external,
                            "total": total,
                            "result": result,
                        })
                    except Exception:
                        continue

        # --- Deduplicate Subjects ---
        unique_subjects = []
        seen = set()
        for s in subjects:
            if s["subject_code"] not in seen:
                seen.add(s["subject_code"])
                unique_subjects.append(s)
        if unique_subjects:
            marksheet_data["subjects"] = unique_subjects

        # --- Remarks Legend ---
        if re.search(r"P->PASS|F->FAIL|A->ABSENT|W->WITHHELD|X->NOT\s+ELIGIBLE", text, re.IGNORECASE):
            marksheet_data["remarks"] = {
                "P": "Pass",
                "F": "Fail",
                "A": "Absent",
                "W": "Withheld",
                "X": "Not Eligible",
            }

        # --- Overall Result ---
        result_block = re.search(r"Result[s]?\s*[:\-]?\s*([A-Za-z\s]+)", text, re.IGNORECASE)
        if result_block:
            marksheet_data["overall_result"] = result_block.group(1).strip().title()

        # --- Percentage / Grade ---
        percent_match = re.search(r"(\d{1,3}\.\d{1,2})\s*%", text)
        if percent_match:
            marksheet_data["percentage"] = percent_match.group(1)

        return marksheet_data

    # -------------------------------------------------------------------------
    def extract_from_image(self, image_path: str) -> dict:
        """Unified pipeline: Donut + OCR + RegexCleaner."""
        print(f"\n📸 Processing: {image_path}")

        donut_result = {}
        try:
            donut_result = self.donut.extract_from_image(image_path)
        except Exception as e:
            print(f"⚠️ Donut extraction failed: {e}")

        ocr_result = self.ocr.ocr(image_path, cls=True)
        lines = [line[1][0] for page in ocr_result for line in page]
        raw_text = " ".join(lines)
        raw_text_clean = re.sub(r"\s+", " ", raw_text).strip()

        ocr_fields = self._extract_fields_from_text(raw_text_clean)
        merged = {**donut_result, **ocr_fields, "raw_ocr_text": raw_text_clean}

        # Detect document type
        doc_type = "Unknown Document"
        if "aadhaar_number" in merged:
            doc_type = "Aadhaar Card"
        elif "pan_number" in merged:
            doc_type = "PAN Card"
        elif "dl_number" in merged:
            doc_type = "Driving License"
        elif re.search(r"\b(university|marks|semester|subject|seat\s*number|result)\b",
                       raw_text_clean, re.IGNORECASE):
            doc_type = "Marksheet"
        merged["document_type"] = doc_type

        if doc_type == "Marksheet":
            marksheet_data = self._extract_marksheet_details(raw_text_clean)
            merged.update(marksheet_data)

        final_output = self.cleaner.clean(raw_text_clean, merged)
        print("\n✅ Hybrid Extracted Data:")
        print(final_output)
        return final_output
