import requests
import os
import json

URL = "http://localhost:5000/process"
DATA_DIR = "data"

files_to_test = [
    "aadhar_sample.jpg",
    "pan_sample.jpg",
    "marksheet_vtu_sample.jpg"
]

print("-" * 50)
print("  EXTRACTED KEY-VALUE OUTPUTS")
print("-" * 50)

for filename in files_to_test:
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        continue
        
    try:
        with open(filepath, 'rb') as f:
            files = {'file': f}
            response = requests.post(URL, files=files)
            
        if response.status_code == 200:
            data = response.json()
            # Truncate face_image for readability in logs
            if "face_image" in data and data["face_image"]:
                data["face_image"] = "<BASE64_STRING_TRUNCATED>"
            
            print(f"\n📄 FILE: {filename}")
            print(json.dumps(data, indent=2))
            print("-" * 30)
        else:
             print(f"❌ Failed to extract {filename}: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
