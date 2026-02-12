from PIL import Image
import os

input_path = "data/marksheet_vtu_sample.webp"
output_path = "data/marksheet_vtu_sample.jpg"

if os.path.exists(input_path):
    img = Image.open(input_path)
    img.convert("RGB").save(output_path, "JPEG")
    print(f"✅ Converted {input_path} to {output_path}")
else:
    print(f"❌ Input file not found: {input_path}")
