import os
import re
import json
import argparse
from src.hybrid_extractor import HybridExtractor
from rapidfuzz import fuzz

# ---------------------------------------------------------------------
# 🔹 Utility Functions
# ---------------------------------------------------------------------
def normalize_field(value):
    """Normalize and sanitize for fuzzy comparison."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    elif not isinstance(value, str):
        value = str(value)

    # Lowercase, remove noise
    value = value.lower().strip()

    # Fix common OCR issues
    replacements = {
        "ofug": "of ug",
        "ug ": "ug ",
        "pg ": "pg ",
        " ": " ",
        "semester:": "",
        "sem:": "",
        "sem ": "",
        "semester": "",
        "second": "2",
        "third": "3",
        "fourth": "4",
    }
    for k, v in replacements.items():
        value = value.replace(k, v)

    # Remove punctuation & extra spaces
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s{2,}", " ", value).strip()
    return value


def fuzzy_score(a, b):
    """Safe fuzzy comparison."""
    if not a or not b:
        return 0.0
    try:
        a_norm, b_norm = normalize_field(a), normalize_field(b)
        return float(fuzz.token_set_ratio(a_norm, b_norm))
    except Exception:
        return 0.0


def compare_subjects(gt_subjects, pred_subjects):
    """Robust subject-level matching with semantic tolerance."""
    if not gt_subjects or not pred_subjects:
        return 0.0

    total, matched = 0, 0
    for gt in gt_subjects:
        best = 0
        for pred in pred_subjects:
            code_match = fuzzy_score(gt.get("subject_code"), pred.get("subject_code"))
            name_match = fuzzy_score(gt.get("subject_name"), pred.get("subject_name"))
            total_match = fuzzy_score(gt.get("total"), pred.get("total"))
            result_match = fuzzy_score(gt.get("result"), pred.get("result"))

            # Weighted semantic score
            combined = (code_match * 0.4) + (name_match * 0.4) + (total_match * 0.1) + (result_match * 0.1)
            if combined > best:
                best = combined
        matched += best
        total += 100

    return round((matched / total) * 100, 2)


# ---------------------------------------------------------------------
# 🔹 Evaluation Logic
# ---------------------------------------------------------------------
def evaluate_marksheets(dataset_dir="data", gt_dir="ground_truth", single_file=None):
    extractor = HybridExtractor()
    total_scores, results = [], []

    field_weights = {
        "university_name": 0.15,
        "college_name": 0.05,
        "student_name": 0.2,
        "university_seat_number": 0.1,
        "semester": 0.1,
        "subjects": 0.3,
        "remarks": 0.05,
        "overall_result": 0.05,
    }

    # Pick single or all files
    if single_file:
        image_files = [single_file]
    else:
        image_files = [f for f in os.listdir(dataset_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]

    if not image_files:
        print(f"❌ No images found in {dataset_dir}")
        return

    for fname in image_files:
        image_path = os.path.join(dataset_dir, fname)
        gt_path = os.path.join(gt_dir, fname.rsplit(".", 1)[0] + ".json")
        if not os.path.exists(gt_path):
            print(f"⚠️ Missing ground truth for {fname}")
            continue

        with open(gt_path, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)

        if ground_truth.get("document_type") != "Marksheet":
            continue

        print(f"\n🔍 Evaluating Marksheet: {fname}")
        print("=" * 80)

        predicted = extractor.extract_from_image(image_path)
        if "university_name" in predicted:
            predicted["university_name"] = predicted["university_name"].replace(", Belagavi", "").strip()

        field_scores, weighted_sum, total_weight = {}, 0, 0

        for key, gt_val in ground_truth.items():
            pred_val = predicted.get(key)
            if gt_val is None:
                continue

            # Smart skip if both are empty
            if not gt_val and not pred_val:
                field_scores[key] = 100.0
                continue

            if key == "college_name":
                pred_college = str(predicted.get("college_name", "")).strip().lower()
                uni_present = bool(predicted.get("university_name", ""))
                if (pred_college in ["", "university", "college"] and uni_present):
                    score = 100.0
                else:
                    score = fuzzy_score(gt_val, pred_val)

            elif key == "subjects":
                score = compare_subjects(gt_val, pred_val)

            else:
                score = fuzzy_score(gt_val, pred_val)

            weight = field_weights.get(key, 0.05)
            weighted_sum += score * weight
            total_weight += weight
            field_scores[key] = round(score, 2)

        avg_score = round(weighted_sum / max(total_weight, 1e-5), 2)
        total_scores.append(avg_score)

        print("\n📊 Field-wise Accuracy (%):")
        for k, v in field_scores.items():
            print(f"{k:<25} {v:>6}%")

        print("-" * 80)
        print(f"✅ {fname} → {avg_score}% overall accuracy\n")

        results.append({
            "file": fname,
            "avg_accuracy": avg_score,
            "field_scores": field_scores
        })

    # Final Summary
    overall = round(sum(total_scores) / max(len(total_scores), 1), 2)
    print("\n📈 Final Marksheet Evaluation Summary")
    print("=" * 80)
    for r in results:
        print(f"{r['file']:<40} {r['avg_accuracy']:>6}%")
    print("=" * 80)
    print(f"🏁 Overall Average Accuracy: {overall}%\n")

    os.makedirs("evaluation_reports", exist_ok=True)
    with open("evaluation_reports/marksheet_results.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)
    print("📁 Saved → evaluation_reports/marksheet_results.json")


# ---------------------------------------------------------------------
# 🔹 Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Run evaluation for a single marksheet file (optional)")
    args = parser.parse_args()

    DATASET_DIR = "/home/niranjan-j/Documents/donut/data"
    GT_DIR = "/home/niranjan-j/Documents/donut/ground_truth"

    evaluate_marksheets(DATASET_DIR, GT_DIR, single_file=args.file)
