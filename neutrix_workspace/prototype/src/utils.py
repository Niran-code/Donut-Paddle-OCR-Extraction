import re
import json
import ast
from rapidfuzz import fuzz


# ------------------------------------------------------
# 🔹 CLEANING + JSON PARSING
# ------------------------------------------------------
def clean_donut_output(raw_output: str):
    """Clean Donut model output and return JSON or dict."""
    text = re.sub(r"<.*?>", "", raw_output)
    json_part = text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(json_part)
    except Exception:
        try:
            return ast.literal_eval(json_part)
        except Exception:
            return {"raw_text": text}


# ------------------------------------------------------
# 🔹 COMMON FIXES FOR OCR MISTAKES
# ------------------------------------------------------
def normalize_text(val: str):
    if not isinstance(val, str):
        return val
    val = val.replace("O", "0").replace("I", "1").replace("B", "8")
    val = val.replace(" ", "").strip()
    return val


# ------------------------------------------------------
# 🔹 FIELD VALIDATORS (Regex)
# ------------------------------------------------------
def validate_and_clean_fields(data: dict):
    """Validate key fields like Aadhaar, PAN, DOB, etc."""
    patterns = {
        "aadhaar": r"^\d{12}$",
        "pan": r"^[A-Z]{5}[0-9]{4}[A-Z]$",
        "dob": r"\b(0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[0-2])[-/]\d{2,4}\b",
        "dl": r"^[A-Z]{2}\d{2}\d{11}$",
    }

    clean_data = {}
    for k, v in data.items():
        val = normalize_text(str(v))
        if re.match(patterns["aadhaar"], val):
            clean_data["aadhaar_number"] = " ".join([val[i:i+4] for i in range(0, 12, 4)])
        elif re.match(patterns["pan"], val):
            clean_data["pan_number"] = val
        elif re.match(patterns["dl"], val):
            clean_data["dl_number"] = val
        elif re.match(patterns["dob"], val):
            clean_data["dob"] = val.replace("-", "/")
        elif any(w in k.lower() for w in ["name", "holder", "candidate"]):
            clean_data["name"] = v.strip()
        elif any(w in k.lower() for w in ["father", "sonof"]):
            clean_data["father_name"] = v.strip()
        else:
            clean_data[k] = v
    return clean_data


# ------------------------------------------------------
# 🔹 DOCUMENT TYPE DETECTOR
# ------------------------------------------------------
def detect_document_type(clean_data: dict):
    text_blob = " ".join(str(v).lower() for v in clean_data.values())

    if re.search(r"\buidai\b|\baadhaar\b|\bvid\b", text_blob):
        return "Aadhaar Card"
    elif re.search(r"\bpan\b|\bpermanent\saccount\snumber\b", text_blob):
        return "PAN Card"
    elif re.search(r"\bdriving\b|\blicen[cs]e\b|dlno", text_blob):
        return "Driving Licence"
    elif re.search(r"\bmarksheet\b|\buniversity\b|\bboard\b|\bsubject\b|\bsemester\b", text_blob):
        return "Marksheet"
    else:
        if "aadhaar_number" in clean_data:
            return "Aadhaar Card"
        if "pan_number" in clean_data:
            return "PAN Card"
        if "dl_number" in clean_data:
            return "Driving Licence"
        return "Unknown Document"


# ------------------------------------------------------
# 🔹 PRETTY PRINTING
# ------------------------------------------------------
def print_boxed(title: str):
    print("\n" + "=" * len(title))
    print(title)
    print("=" * len(title))



