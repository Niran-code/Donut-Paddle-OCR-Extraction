import argparse
import os
import sys
from src.batch_runner import run_batch
from src.extract import DonutExtractor
from src.utils import print_boxed, evaluate_accuracy
from src.hybrid_extractor import HybridExtractor


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["single", "batch", "hybrid", "evaluate"],  # ✅ added evaluate
        default="single",
        help="Choose extraction mode: single | batch | hybrid | evaluate"
    )
    parser.add_argument("--image", help="Path to image for single/hybrid/evaluate mode")
    args = parser.parse_args()

    # --- Single Image Mode (Donut only) ---
    if args.mode == "single":
        if not args.image:
            print("❌ Please provide --image path")
        else:
            print_boxed("Single Image Extraction (Donut)")
            extractor = DonutExtractor()
            data = extractor.extract_from_image(args.image)
            print("\n✅ Extracted Data (Donut Only):")
            print(data)

    # --- Batch Mode ---
    elif args.mode == "batch":
        print_boxed("Batch Extraction Mode")
        run_batch()

    # --- Hybrid Mode (Donut + PaddleOCR) ---
    elif args.mode == "hybrid":
        if not args.image:
            print("❌ Please provide --image path")
        else:
            print_boxed("Hybrid Extraction (Donut + PaddleOCR)")
            extractor = HybridExtractor()
            data = extractor.extract_from_image(args.image)
            print("\n✅ Hybrid Extracted Data:")
            print(data)

    # --- Evaluation Mode (Hybrid + Ground Truth Compare) ---
    elif args.mode == "evaluate":
        if not args.image:
            print("❌ Please provide --image path")
            sys.exit(1)

        print_boxed("Evaluation Mode (Hybrid + Ground Truth Comparison)")
        extractor = HybridExtractor()

        # Extract data first
        data = extractor.extract_from_image(args.image)

        # Ground Truth JSON path
        gt_name = os.path.splitext(os.path.basename(args.image))[0] + ".json"
        gt_path = os.path.join("ground_truth", gt_name)

        if not os.path.exists(gt_path):
            print(f"⚠️ Missing ground truth file: {gt_path}")
            print("💡 Please place a JSON file with the same name under /ground_truth/")
            sys.exit(1)

        # Evaluate
        print("\n📘 Comparing extracted data with ground truth...\n")
        evaluate_accuracy(args.image, data, gt_path)
