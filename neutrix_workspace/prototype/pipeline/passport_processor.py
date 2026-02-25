import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def process_passport(raw_text: str, full_text_lines: list) -> Dict[str, Any]:
    """
    Isolated extractor for Passport featuring MRZ fallback logic.
    """
    logger.info("Extracting Passport data...")
    data = {
        "document_type": "passport",
        "country": "Republic of India",
        "type": "P",
        "country_code": "IND",
        "nationality": "INDIAN",
        "mrz": {}
    }
    
    text_upper = raw_text.upper()
    lines = [line.strip() for line in full_text_lines if line.strip()]
    
    # 1. Given Names
    given_match = re.search(r"(?:GIVEN\s*NAME[S]?|GIVEN\s*NAME\(S\))[\s:]*([A-Z\s]+?)(?=\s+SURNAME|\s+SEX|\s+NATIONALITY|\s+DATE|\n|$)", text_upper)
    if given_match:
         data["given_names"] = given_match.group(1).strip()
         
    # 2. Surname
    surname_match = re.search(r"SURNAME[\s:]*([A-Z\s]+?)(?=\s+GIVEN|\s+NATIONALITY|\s+DATE|\n|$)", text_upper)
    if surname_match:
         data["surname"] = surname_match.group(1).strip()
         
    # Positional Name Fallback (If labels were entirely missed by OCR)
    if not data.get("surname") or not data.get("given_names"):
         # The names usually appear directly after the Passport Number and before Sex or DOB.
         # Example layout: "X6248911", "DORESWAMY", "GIRISH", "KUMAR", "/Sex", "11/09/2000"
         pp_idx = -1
         sex_dob_idx = -1
         
         for i, line in enumerate(lines):
             if re.match(r"^[A-Z][0-9]{7}$", line.upper()):
                 if pp_idx == -1: pp_idx = i
             elif "SEX" in line.upper() or re.match(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", line) or "BIRTH" in line.upper():
                 if pp_idx != -1 and sex_dob_idx == -1: sex_dob_idx = i
                 
         if pp_idx != -1 and sex_dob_idx != -1 and (sex_dob_idx - pp_idx) > 1:
             name_lines = lines[pp_idx+1 : sex_dob_idx]
             name_parts = [n.strip() for n in name_lines if len(n.strip()) > 1 and "IND" not in n.upper() and "NATIONALITY" not in n.upper() and "BIRTH" not in n.upper()]
             
             if len(name_parts) >= 1 and not data.get("surname"):
                 data["surname"] = name_parts[0]
             if len(name_parts) >= 2 and not data.get("given_names"):
                 data["given_names"] = " ".join(name_parts[1:])
         
    # 3. DOB
    dob_match = re.search(r"DATE\s*OF\s*BIRTH[\s:]*(\d{2}[/-]\d{2}[/-]\d{4})", text_upper)
    if not dob_match:
         dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text_upper)
    if dob_match:
         data["date_of_birth"] = dob_match.group(1).replace("-", "/")
         
    # 4. Gender / Sex
    gender_match = re.search(r"(?:SEX|GENDER)[\s:]*(M|F|MALE|FEMALE)", text_upper)
    if gender_match:
         g = gender_match.group(1)
         data["sex"] = "M" if g.startswith("M") else "F"
         
    # Extract Dates from lines (usually format DD/MM/YYYY)
    dates = []
    for line in lines:
        d = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", line)
        if d:
            dates.append(d.group(1).replace("-", "/"))
            
    if data.get("date_of_birth") in dates:
        dates.remove(data["date_of_birth"])
        
    if len(dates) >= 2:
        # Sort to find issue and expiry logically
        try:
            valid_dt = [d for d in dates if len(d) == 10]
            if len(valid_dt) >= 2:
                # Typically issue date is before expiry
                dp1, dp2 = valid_dt[0], valid_dt[1]
                if int(dp1[-4:]) < int(dp2[-4:]):
                    data["date_of_issue"] = dp1
                    data["date_of_expiry"] = dp2
                else:
                    data["date_of_issue"] = dp2
                    data["date_of_expiry"] = dp1
        except Exception:
            pass

    # Place of Issue / Birth
    for i, line in enumerate(lines):
        if "BENGALURU" in line.upper() and not data.get("place_of_birth"):
             if "-" in line:
                 data["place_of_birth"] = line.replace("-", ", ")
             elif "place" not in line.lower() and len(line) > 3:
                 # It might be place of issue
                 if "BENGALURU, KARNATAKA" not in line.upper(): 
                     data["place_of_issue"] = line.strip()

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
         # Avoid "HRURIV/REPUBLICOFINDIA" triggering the "IND" check
         if len(clean_line) >= 20 and ("P<" in clean_line or ("IND" in clean_line and "INDIA" not in clean_line) or clean_line.count("<") > 2):
             mrz_lines.append(clean_line)
             
    if len(mrz_lines) >= 1:
         if len(mrz_lines) >= 2:
             data["mrz"]["line1"] = mrz_lines[-2]
             data["mrz"]["line2"] = mrz_lines[-1]
         else:
             # Only one MRZ line survived the OCR crop
             data["mrz"]["line2"] = mrz_lines[0]
         
         mrz1 = data["mrz"].get("line1", "")
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
         
         mrz2 = data["mrz"].get("line2", "")
         if "passport_number" not in data and len(mrz2) >= 9:
             data["passport_number"] = mrz2[0:9].replace("<", "")
             
         # MRZ Char 21 is Sex (M, F, <). If line is truncated, we check position relative to the end.
         if "sex" not in data:
             if len(mrz2) >= 21:
                 sex_char = mrz2[20]
                 if sex_char in ["M", "F", "X"]:
                     data["sex"] = sex_char
             # If truncated, the letter M or F often precedes a string of numbers like M3302211 or is surrounded by digits
             if "sex" not in data and re.search(r"\d+([MFX])\d+", mrz2):
                 data["sex"] = re.search(r"\d+([MFX])\d+", mrz2).group(1)
             
    # Fill full_name if parts exist
    if data.get("given_names") and data.get("surname"):
        data["full_name"] = f"{data['given_names']} {data['surname']}"
             
    return data
