import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def process_driving_license(raw_text: str, lines: list) -> Dict[str, Any]:
    """
    Isolated extractor for Driving License.
    """
    logger.info("Extracting Driving License data...")
    data = {"document_type": "Driving License"}
    
    text_upper = raw_text.upper()
    
    # 1. DL NUMBER (STRICT-ISH)
    dl_match = re.search(r"DL\s*NO\.?\s*[:\-]?\s*([A-Z0-9 ]+)", text_upper)
    if not dl_match:
         # Fallback check for just the raw format
         dl_match_raw = re.search(r"\b([A-Z]{2}[0-9]{2}[0-9\s-]{7,15})\b", text_upper)
         if dl_match_raw:
             raw_dl = dl_match_raw.group(1)
             dl_number = re.sub(r"[^A-Z0-9]", "", raw_dl)
             if len(dl_number) >= 11:
                 data["dl_number"] = dl_number
    else:
        raw_dl = dl_match.group(1)
        dl_number = re.sub(r"[^A-Z0-9]", "", raw_dl)
        if re.match(r"^[A-Z]{2}[0-9]{2}[0-9]{7,}$", dl_number):
            data["dl_number"] = dl_number

    # 2. NAME (RELAXED LABEL MATCH)
    # OCR joins all lines with spaces. So NAME is followed by some text, terminating at DOB or S/W/D
    name_match = re.search(r"NAME\s*[:\-]?\s*([A-Za-z\s]+?)(?=\s+D\.?O\.?B|\s+S/W/D|\s+DOB|$)", text_upper)
    if name_match:
        name_str = name_match.group(1).strip()
        name_str = re.sub(r"[^A-Z\s]", "", name_str).strip()
        if len(name_str) > 3 and not any(x in name_str for x in ["HOLDER", "SIGN", "AUTHORITY"]):
            data["name"] = name_str

    # 3. DOB (STRICT LABEL MATCH)
    dob_match = re.search(r"D\.?O\.?B\.?\s*[:\-]?\s*(\d{2}-\d{2}-\d{4})", text_upper)
    if dob_match:
        data["dob"] = dob_match.group(1)

    # 4. VALID TILL (STRICT)
    valid_match = re.search(r"VALID\s*TILL\s*[:\-]?\s*(\d{2}-\d{2}-\d{4})", text_upper)
    if valid_match:
        data["valid_till"] = valid_match.group(1)

    # 5. ADDRESS (CONTROLLED BLOCK EXTRACTION)
    address_block = re.search(
        r"ADDRESS\s*[:\-]?\s*(.*?)\s*(SIGN\.|SIGN\s+LICENCING|SIGN|HOLDER|$)",
        text_upper,
        re.DOTALL
    )
    if address_block:
        raw_address = address_block.group(1)
        raw_address = raw_address.replace('\n', ' ').replace('\r', ' ')
        raw_address = re.sub(r'\s+', ' ', raw_address)
        data["address"] = raw_address.strip()
        
    return data
