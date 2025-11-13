import re
from datetime import datetime


class RegexCleaner:
    """
    Cleans and normalizes OCR + Donut extracted text.
    ✅ Works for:
       - Aadhaar Cards
       - PAN Cards
       - University Mark Sheets (college/university normalization)
    """

    def __init__(self):
        # Common Aadhaar patterns
        self.aadhaar_pattern = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
        self.yob_pattern = re.compile(r"Year\s*of\s*Birth\s*[:\-]?\s*(\d{4})", re.IGNORECASE)
        self.date_pattern = re.compile(r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b")
        self.gender_pattern = re.compile(r"\b(MALE|FEMALE|Male|Female|M|F)\b")
        self.noise_context = re.compile(r"(download|issue|vid|valid|update|generated|uid)", re.IGNORECASE)

    # -------------------------------------------------------------------------
    def _normalize_date(self, date_str: str) -> str:
        """Convert DD/MM/YYYY → YYYY-MM-DD"""
        try:
            clean = date_str.replace(".", "/").replace("-", "/")
            return datetime.strptime(clean, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            return date_str

    # -------------------------------------------------------------------------
    def _extract_aadhaar_number(self, text: str) -> str:
        """Extract Aadhaar number in 4-4-4 format."""
        match = self.aadhaar_pattern.search(text)
        if match:
            digits = match.group().replace(" ", "")
            return f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"
        return None

    # -------------------------------------------------------------------------
    def _extract_dob_or_yob(self, text: str) -> str:
        """Extract DOB or Year of Birth."""
        yob_match = self.yob_pattern.search(text)
        if yob_match:
            return f"{yob_match.group(1)}-01-01"

        for date_str in self.date_pattern.findall(text):
            context = text[max(0, text.find(date_str) - 25): text.find(date_str)]
            if not self.noise_context.search(context):
                return self._normalize_date(date_str)
        return None

    # -------------------------------------------------------------------------
    def _extract_name(self, text: str) -> str:
        """Extract person name (for Aadhaar, PAN, Marksheet)."""
        text = re.sub(r"\s+", " ", text)
        patterns = [
            r"(?:Name|NAME|नाम)[:\s]*([A-Z][A-Za-z\s]+)",
            r"Government of India.*?([A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+)(?=.*?(?:Year|DOB|Male|Female|/DOB))",
            r"([A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+)(?=\s*(?:Year|DOB|Male|Female))"
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                candidate = m.group(1).strip().title()
                if not re.search(r"\d", candidate) and 1 <= len(candidate.split()) <= 3:
                    blacklist = {"Download", "Issue", "Government", "India", "Date", "Year"}
                    if not any(b in candidate for b in blacklist):
                        return candidate
        return None

    # -------------------------------------------------------------------------
    def _extract_gender(self, text: str) -> str:
        """Detect gender only if explicitly stated."""
        text = re.sub(r"\s+", " ", text)
        clean_zone = re.split(r"(Nomenclature|Abbreviations)", text, 1, flags=re.IGNORECASE)[0]

        male_match = re.search(r"\bMALE\b", clean_zone, re.IGNORECASE)
        female_match = re.search(r"\bFEMALE\b", clean_zone, re.IGNORECASE)

        if not male_match and not female_match:
            return None
        if male_match and female_match:
            return "Male" if male_match.start() < female_match.start() else "Female"
        if male_match:
            return "Male"
        if female_match:
            return "Female"
        return None

    # -------------------------------------------------------------------------
    def _normalize_college_name(self, text: str) -> str:
        """Normalize college/university names (non-hardcoded)."""
        if not text or not isinstance(text, str):
            return None

        # Remove punctuation (keep dots for initials)
        text = re.sub(r"[^A-Za-z0-9\.\s]", " ", text)

        # Merge spaced acronyms like "V T U" → "VTU"
        text = re.sub(r"\b([A-Z])\s+([A-Z])\b", r"\1\2", text)

        # Fix acronyms like "V.T.U." → "VTU"
        text = re.sub(r"\b([A-Z])\.(?=[A-Z])", r"\1", text)

        # Clean excessive whitespace
        text = re.sub(r"\s{2,}", " ", text.strip())

        # Title case except known acronyms
        words = []
        for word in text.split():
            if word.isupper() and len(word) <= 5:
                words.append(word)
            else:
                words.append(word.capitalize())
        normalized = " ".join(words)

        # Drop location suffixes
        normalized = re.sub(r"\b(Belagavi|Belgaum|Karnataka|India)\b", "", normalized, flags=re.IGNORECASE).strip()

        # Remove leading/trailing keywords like "The" or "Of"
        normalized = re.sub(r"^(The\s+|Of\s+)", "", normalized, flags=re.IGNORECASE).strip()

        return normalized if len(normalized) > 3 else None

    # -------------------------------------------------------------------------
    def clean(self, raw_text: str, extracted_fields: dict) -> dict:
        """Main cleanup and normalization pipeline."""
        clean_data = {}

        # Aadhaar-related cleaning
        aadhaar = self._extract_aadhaar_number(raw_text)
        if aadhaar:
            clean_data["aadhaar_number"] = aadhaar

        dob = self._extract_dob_or_yob(raw_text)
        if dob:
            clean_data["dob"] = dob

        name = self._extract_name(raw_text)
        if name:
            clean_data["name"] = name

        gender = self._extract_gender(raw_text)
        if gender:
            clean_data["gender"] = gender

        # College / University normalization
        if "college_name" in extracted_fields:
            normalized_college = self._normalize_college_name(extracted_fields["college_name"])
            if normalized_college:
                clean_data["college_name"] = normalized_college

        if "university_name" in extracted_fields:
            normalized_uni = self._normalize_college_name(extracted_fields["university_name"])
            if normalized_uni:
                clean_data["university_name"] = normalized_uni

        # Merge cleaned data
        final = {**extracted_fields, **clean_data}

        # Remove noise keys
        for k in list(final.keys()):
            if any(x in k.lower() for x in ["download", "issue", "vid", "generated"]):
                final.pop(k, None)

        # Auto-document classification
        if "aadhaar_number" in final:
            final["document_type"] = "Aadhaar Card"
        elif re.search(r"university|marks|semester|subject", raw_text, re.IGNORECASE):
            final["document_type"] = "Marksheet"
        elif "pan_number" in final:
            final["document_type"] = "PAN Card"

        return final
