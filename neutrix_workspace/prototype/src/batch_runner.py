import os, pandas as pd
from tqdm import tqdm
from .hybrid_extractor import HybridExtractor

def run_batch(input_folder="data", output_folder="outputs"):
    os.makedirs(f"{output_folder}/json", exist_ok=True)
    os.makedirs(f"{output_folder}/csv", exist_ok=True)

    print("🚀 Initializing Batch Extraction (Hybrid Mode) ...")
    extractor = HybridExtractor()
    results = []

    for fname in tqdm(os.listdir(input_folder)):
        if not fname.lower().endswith((".jpg", ".png", ".jpeg", ".webp")):
            continue
        path = os.path.join(input_folder, fname)
        print(f"\n📄 Processing {fname} ...")
        try:
            kv_data = extractor.extract_from_image(path)
            results.append({"filename": fname, **kv_data})
            with open(f"{output_folder}/json/{fname}.json", "w") as f:
                f.write(str(kv_data))
        except Exception as e:
            print(f"❌ Error processing {fname}: {e}")

    if results:
        df = pd.DataFrame(results)
        df.to_csv(f"{output_folder}/csv/extracted_data.csv", index=False)
        print("\n✅ Extraction complete. CSV saved in outputs/csv/")
    else:
        print("\n⚠️ No results found.")
