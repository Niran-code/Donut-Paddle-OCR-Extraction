import os
import json
from src.hybrid_extractor import HybridExtractor
from rapidfuzz import fuzz

# ---------------------------------------------------------------------
# 🔹 Fuzzy Scoring Utilities
# ---------------------------------------------------------------------
def fuzzy_score(a: str, b: str) -> float:
    """Compute fuzzy match percentage."""
    if not a or not b:
        return 0.0
    return float(fuzz.token_sort_ratio(str(a), str(b)))


def numeric_score(a, b) -> float:
    """Exact numeric comparison (for DOB, PAN, Aadhaar)."""
    try:
        return 100.0 if str(a).strip() == str(b).strip() else 0.0
    except Exception:
        return 0.0


def compare_lists(gt_list, pred_list):
    """Compare list fields such as subject tables."""
    if not gt_list or not pred_list:
        return 0.0
    total = 0
    for gt_item in gt_list:
        best = 0
        for pred_item in pred_list:
            score = fuzzy_score(str(gt_item), str(pred_item))
            if score > best:
                best = score
        total += best
    return round(total / len(gt_list), 2)


# ---------------------------------------------------------------------
# 🔹 Evaluation Logic
# ---------------------------------------------------------------------
def evaluate(dataset_dir="data", gt_dir="ground_truth"):
    """
    Evaluate extracted data against ground truth JSONs.
    Skips optional fields and uses weighted accuracy scoring.
    """
    extractor = HybridExtractor()
    total_scores = []
    results = []

    # Fields and their weights (critical ones contribute more)
    field_weights = {
        "document_type": 0.05,
        "name": 0.1,
        "father_name": 0.05,
        "dob": 0.1,
        "aadhaar_number": 0.1,
        "pan_number": 0.1,
        "university_name": 0.15,
        "student_name": 0.15,
        "university_seat_number": 0.1,
        "semester": 0.05,
        "subjects": 0.15,
    }

    # Optional fields (don’t penalize if missing)
    optional_fields = {"college_name", "remarks", "semester_1", "semester_2"}

    image_files = [
        f for f in os.listdir(dataset_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    if not image_files:
        print(f"❌ No valid image files found in {dataset_dir}")
        return

    for fname in image_files:
        image_path = os.path.join(dataset_dir, fname)
        gt_path = os.path.join(gt_dir, fname.rsplit(".", 1)[0] + ".json")

        if not os.path.exists(gt_path):
            print(f"⚠️ Missing ground truth for {fname}")
            continue

        print(f"\n🔍 Evaluating {fname} ...")
        print("=" * 70)

        # Run extractor
        predicted = extractor.extract_from_image(image_path)

        # Load ground truth
        with open(gt_path, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)

        # Normalize location noise for fair comparison
        if "university_name" in predicted:
            predicted["university_name"] = predicted["university_name"].replace(", Belagavi", "").strip()

        # Compare each field
        field_scores = {}
        weighted_sum = 0
        total_weight = 0

        for key, gt_val in ground_truth.items():
            pred_val = predicted.get(key)

            # Skip optional fields entirely if absent
            if key in optional_fields and (not pred_val):
                continue

            if isinstance(gt_val, list) and isinstance(pred_val, list):
                score = compare_lists(gt_val, pred_val)
            elif key in ["dob", "aadhaar_number", "pan_number"]:
                score = numeric_score(gt_val, pred_val)
            else:
                score = fuzzy_score(gt_val, pred_val)

            weight = field_weights.get(key, 0.05)
            weighted_sum += score * weight
            total_weight += weight
            field_scores[key] = round(score, 2)

        avg_score = round(weighted_sum / max(total_weight, 1e-5), 2)
        total_scores.append(avg_score)

        # Display field-wise details
        print("\n📊 Field-wise Accuracy (%):")
        for field, score in field_scores.items():
            gt_val = ground_truth.get(field)
            pred_val = predicted.get(field)
            print(f"{field:<25} {score:>6}%  | GT: {gt_val} | Pred: {pred_val}")

        print("-" * 70)
        print(f"✅ {fname} → {avg_score}% overall weighted accuracy\n")

        results.append({
            "file": fname,
            "avg_accuracy": avg_score,
            "field_scores": field_scores
        })

    # -----------------------------------------------------------------
    # Final Summary
    # -----------------------------------------------------------------
    overall = round(sum(total_scores) / max(len(total_scores), 1), 2)
    print("\n📈 Final Evaluation Summary")
    print("=" * 70)
    for r in results:
        print(f"{r['file']:<40} {r['avg_accuracy']:>6}%")
    print("=" * 70)
    print(f"🏁 Overall Average Accuracy: {overall}%\n")

    os.makedirs("evaluation_reports", exist_ok=True)
    with open("evaluation_reports/results.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)
    print("📁 Saved detailed report → evaluation_reports/results.json")


# ---------------------------------------------------------------------
# 🔹 Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    DATASET_DIR = "/home/niranjan-j/Documents/donut/data"
    GT_DIR = "/home/niranjan-j/Documents/donut/ground_truth"
    evaluate(DATASET_DIR, GT_DIR)
