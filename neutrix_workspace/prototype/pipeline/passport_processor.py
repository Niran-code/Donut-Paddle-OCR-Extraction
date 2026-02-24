import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def process_passport(raw_text: str, lines: list) -> Dict[str, Any]:
    """
    Isolated extractor for Passport featuring MRZ fallback logic.
    """
    logger.info("Extracting Passport data...")
    data = {"document_type": "passport"}
    
    text_upper = raw_text.upper()
    
    # 1. Given Names
    given_match = re.search(r"(?:GIVEN\s*NAME[S]?|GIVEN\s*NAME\(S\))[\s:]*([A-Z\s]+?)(?=\s+SURNAME|\s+SEX|\s+NATIONALITY|\s+DATE|\n|$)", text_upper)
    if given_match:
         data["given_names"] = given_match.group(1).strip()
         
    # 2. Surname
    surname_match = re.search(r"SURNAME[\s:]*([A-Z\s]+?)(?=\s+GIVEN|\s+NATIONALITY|\s+DATE|\n|$)", text_upper)
    if surname_match:
         data["surname"] = surname_match.group(1).strip()
         
    # 3. DOB
    dob_match = re.search(r"DATE\s*OF\s*BIRTH[\s:]*(\d{2}[/-]\d{2}[/-]\d{4})", text_upper)
    if not dob_match:
         dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text_upper)
    if dob_match:
         data["date_of_birth"] = dob_match.group(1).replace("/", "-")
         
    # 4. Gender
    gender_match = re.search(r"(?:SEX|GENDER)[\s:]*(M|F|MALE|FEMALE)", text_upper)
    if gender_match:
         g = gender_match.group(1)
         data["gender"] = "Male" if g.startswith("M") else "Female"
         
    # 5. Passport Number (Strict layout or MRZ fragment fallback)
    passport_match = re.search(r"PASSPORT\s*N[O0]\.?[\s:]*([A-Z][0-9]{7})", text_upper)
    if passport_match:
         data["passport_number"] = passport_match.group(1)
    else:
         raw_pp = re.search(r"\b([A-Z][0-9]{7})\b", text_upper)
         if raw_pp:
             data["passport_number"] = raw_pp.group(1)

    # 6. MRZ Line Fallbacks (Since Paddle OCR often mangles the '<' into spaces)
    mrz_lines = []
    for line in lines:
         clean_line = line.replace(" ", "")
         if len(clean_line) >= 30 and ("P<" in clean_line or "IND" in clean_line or clean_line.count("<") > 3):
             mrz_lines.append(clean_line)
             
    if len(mrz_lines) >= 2:
         data["mrz_line1"] = mrz_lines[-2]
         data["mrz_line2"] = mrz_lines[-1]
         
         mrz1 = data["mrz_line1"]
         # Extract Names from MRZ1: P<countrySURNAME<<GIVEN<NAMES
         if "<" in mrz1 and ("surname" not in data or "given_names" not in data):
              try:
                  # Strip the P<IND preface
                  parts = mrz1[5:].split("<<")
                  if len(parts) >= 2:
                       if "surname" not in data:
                           data["surname"] = parts[0].replace("<", " ").strip()
                       if "given_names" not in data:
                           data["given_names"] = parts[1].replace("<", " ").strip()
              except Exception as e:
                  logger.debug(f"MRZ name parsing failed: {e}")
         
         mrz2 = data["mrz_line2"]
         if "passport_number" not in data and len(mrz2) >= 9:
             data["passport_number"] = mrz2[0:9].replace("<", "")
             
    return data
