import argparse
import os
import sys
from src.batch_runner import run_batch
from src.hybrid_extractor import HybridExtractor
from src.utils import print_boxed
from src.evaluate import Evaluator


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["single", "batch", "evaluate"],
        default="single",
        help="Choose extraction mode: single | batch | evaluate"
    )
    parser.add_argument("--image", help="Path to image for single/evaluate mode")
    parser.add_argument("--gt", help="Path to ground truth JSON for evaluate mode (optional)", default=None)
    args = parser.parse_args()

    # --- Single Image Mode (Hybrid) ---
    if args.mode == "single":
        if not args.image:
            print("❌ Please provide --image path")
        else:
            print_boxed("Single Image Extraction (Hybrid: Donut + PaddleOCR)")
            extractor = HybridExtractor()
            data = extractor.extract_from_image(args.image)
            print("\n✅ Extracted Data:")
            print(data)

    # --- Batch Mode ---
    elif args.mode == "batch":
        print_boxed("Batch Extraction Mode (Hybrid)")
        run_batch()

    # --- Evaluation Mode ---
    elif args.mode == "evaluate":
        evaluator = Evaluator()
        
        if args.image:
            # Single Image Evaluation
            print_boxed("Evaluation Mode (Single Image)")
            evaluator.evaluate_single(args.image, args.gt)
        else:
            # Batch Evaluation
            print_boxed("Evaluation Mode (Batch - All Data)")
            evaluator.evaluate_batch()
