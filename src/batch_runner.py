import os, pandas as pd
from tqdm import tqdm
from .extract import DonutExtractor

def run_batch(input_folder="data", output_folder="outputs"):
    os.makedirs(f"{output_folder}/json", exist_ok=True)
    os.makedirs(f"{output_folder}/csv", exist_ok=True)

    extractor = DonutExtractor()
    results = []

    for fname in tqdm(os.listdir(input_folder)):
        if not fname.lower().endswith((".jpg", ".png", ".jpeg")):
            continue
        path = os.path.join(input_folder, fname)
        print(f"\n📄 Processing {fname} ...")
        kv_data = extractor.extract_from_image(path)
        results.append({"filename": fname, **kv_data})
        with open(f"{output_folder}/json/{fname}.json", "w") as f:
            f.write(str(kv_data))

    df = pd.DataFrame(results)
    df.to_csv(f"{output_folder}/csv/extracted_data.csv", index=False)
    print("\n✅ Extraction complete. CSV saved in outputs/csv/")
