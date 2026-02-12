import requests
import os
import json

URL = "http://localhost:5000/process"
DATA_DIR = "data"

files_to_test = [
    "aadhar_sample.jpg",
    "pan_sample.jpg",
    "marksheet_vtu_sample.webp"
]

for filename in files_to_test:
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"⚠️ File not found: {filepath}")
        continue
        
    print(f"\n🚀 Testing {filename}...")
    try:
        with open(filepath, 'rb') as f:
            files = {'file': f}
            response = requests.post(URL, files=files)
            
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Doc Type: {data.get('document_type', 'Unknown')}")
            print(f"   Confidence: {data.get('ocr_accuracy_score', 0)}%")
            print(f"   Face Extracted: {'Yes' if data.get('face_image') else 'No'}")
            # print(json.dumps(data, indent=2)) # meaningful output
        else:
             print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
