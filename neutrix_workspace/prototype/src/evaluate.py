import os
import json
import re
from rapidfuzz import fuzz
from .hybrid_extractor import HybridExtractor
from tqdm import tqdm
import pandas as pd

# ---------------------------------------------------------------------
# 🔹 Scoring Utilities
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
    valid_items = 0
    # Simple strategy: for each GT item, find best match in Pred
    for gt_item in gt_list:
        best = 0
        gt_str = json.dumps(gt_item, sort_keys=True)
        for pred_item in pred_list:
            pred_str = json.dumps(pred_item, sort_keys=True)
            score = fuzzy_score(gt_str, pred_str)
            if score > best:
                best = score
        total += best
        valid_items += 1
    
    return round(total / max(valid_items, 1), 2)

# ---------------------------------------------------------------------
# 🔹 Evaluation Logic
# ---------------------------------------------------------------------

class Evaluator:
    def __init__(self):
        self.extractor = HybridExtractor()

    def evaluate_single(self, image_path: str, gt_path: str = None):
        """
        Evaluate a single image against its ground truth.
        If gt_path is not provided, tries to find it in "ground_truth/<name>.json".
        """
        if not gt_path:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            gt_path = os.path.join(os.path.dirname(os.path.dirname(image_path)), "ground_truth", f"{base_name}.json")
            if not os.path.exists(gt_path):
                 # fallback to local ground_truth folder if relative path fails
                 gt_path = os.path.join("ground_truth", f"{base_name}.json")

        if not os.path.exists(gt_path):
            print(f"⚠️ Missing ground truth file: {gt_path}")
            return None

        print(f"🔍 Evaluating {os.path.basename(image_path)} ...")
        
        # 1. Extract
        predicted = self.extractor.extract_from_image(image_path)

        # 2. Load GT
        with open(gt_path, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)

        # 3. Compare
        field_scores = {}
        weighted_sum = 0
        total_weight = 0

        # Define weights
        weights = {
            "name": 0.15,
            "aadhaar_number": 0.2,
            "pan_number": 0.2,
            "dob": 0.1,
            "university_name": 0.1,
            "student_name": 0.1,
            "university_seat_number": 0.1,
            "subjects": 0.3,
            "document_type": 0.05
        }

        # Compare fields present in GT
        for key, gt_val in ground_truth.items():
            pred_val = predicted.get(key)
            
            if isinstance(gt_val, list) and isinstance(pred_val, list):
                score = compare_lists(gt_val, pred_val)
            elif key in ["dob", "aadhaar_number", "pan_number"]:
                score = numeric_score(gt_val, pred_val)
            else:
                score = fuzzy_score(gt_val, pred_val)
            
            w = weights.get(key, 0.05)
            weighted_sum += score * w
            total_weight += w
            field_scores[key] = round(score, 2)

        avg_score = round(weighted_sum / max(total_weight, 1e-5), 2)
        
        print("\n📊 Field-wise Accuracy (%):")
        for k, s in field_scores.items():
            print(f"{k:<25} {s:>6}%")
        print("-" * 50)
        print(f"✅ Overall Score: {avg_score}%\n")

        return {
            "file": os.path.basename(image_path),
            "score": avg_score,
            "details": field_scores,
            "predicted": predicted,
            "ground_truth": ground_truth
        }

    def evaluate_batch(self, dataset_dir="data", gt_dir="ground_truth"):
        """Run evaluation on a whole folder."""
        if not os.path.exists(dataset_dir) or not os.path.exists(gt_dir):
            print("❌ Data or Ground Truth directory missing.")
            return

        image_files = [f for f in os.listdir(dataset_dir) if f.lower().endswith((".jpg", ".png", ".jpeg", ".webp"))]
        results = []

        print(f"🚀 Starting Batch Evaluation on {len(image_files)} files...")

        for fname in tqdm(image_files):
            img_path = os.path.join(dataset_dir, fname)
            gt_path = os.path.join(gt_dir, os.path.splitext(fname)[0] + ".json")
            
            res = self.evaluate_single(img_path, gt_path)
            if res:
                results.append(res)

        # Summary
        if results:
            avg_all = sum(r['score'] for r in results) / len(results)
            print("\n📈 Batch Evaluation Summary")
            print("=" * 50)
            for r in results:
                print(f"{r['file']:<30} {r['score']:>6}%")
            print("-" * 50)
            print(f"🏁 Average Dataset Accuracy: {avg_all:.2f}%")
            
            # Save report
            os.makedirs("outputs", exist_ok=True)
            with open("outputs/evaluation_report.json", "w") as f:
                json.dump(results, f, indent=2)
            print("📁 Report saved to outputs/evaluation_report.json")
