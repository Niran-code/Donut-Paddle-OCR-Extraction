import re, json, ast
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


# ------------------------------------------------------
# 🔹 EVALUATION HELPERS
# ------------------------------------------------------
def _fuzzy_score(a: str, b: str):
    if not a or not b:
        return 0.0
    return float(fuzz.token_sort_ratio(str(a), str(b)))


def _num_score(a, b):
    try:
        return 100.0 if str(a).strip() == str(b).strip() else 0.0
    except Exception:
        return 0.0


def _compare_subjects(gt_list, pred_list):
    """Compare subject tables between GT and predicted."""
    if not gt_list or not pred_list:
        return 0.0

    # Convert subjects to simplified comparison strings
    gt_flat = [" ".join(str(gt.get(k, "")) for k in ["subject_code", "total", "result"]) for gt in gt_list]
    pred_flat = [" ".join(str(p.get(k, "")) for k in ["subject_code", "total", "result"]) for p in pred_list]

    matched = 0
    for gt in gt_flat:
        best = max((_fuzzy_score(gt, p) for p in pred_flat), default=0)
        if best >= 80:
            matched += 1

    return round((matched / len(gt_flat)) * 100, 2)


# ------------------------------------------------------
# 🔹 MAIN EVALUATION FUNCTION
# ------------------------------------------------------
def evaluate_accuracy(image_path: str, extracted: dict, gt_path: str):
    """Compare extracted fields vs ground truth JSON."""
    import os

    if not os.path.exists(gt_path):
        print(f"⚠️ Ground truth not found: {gt_path}")
        return

    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    total_score, count = 0, 0
    results = {}

    # Core fields for all doc types
    fields = [
        "document_type", "name", "dob", "gender",
        "aadhaar_number", "pan_number", "father_name",
        "university_name", "student_name", "university_seat_number",
        "semester", "subjects"
    ]

    for field in fields:
        gt_val = ground_truth.get(field)
        pred_val = extracted.get(field)
        if gt_val is None:
            continue

        # Select comparison method
        if field == "subjects" and isinstance(gt_val, list) and isinstance(pred_val, list):
            score = _compare_subjects(gt_val, pred_val)
        elif field in ["dob", "aadhaar_number", "pan_number"]:
            score = _num_score(gt_val, pred_val)
        else:
            score = _fuzzy_score(gt_val, pred_val)

        results[field] = {"gt": gt_val, "pred": pred_val, "score": round(score, 2)}
        total_score += score
        count += 1

    avg = round(total_score / max(count, 1), 2)

    # Summary display
    print("\n📊 Evaluation Summary\n" + "=" * 40)
    for k, v in results.items():
        print(f"{k}: {v['score']}% (GT: {v['gt']} | Pred: {v['pred']})")
    print("=" * 40)
    print(f"\n🏁 Overall Average Accuracy: {avg}%\n")

    return avg
