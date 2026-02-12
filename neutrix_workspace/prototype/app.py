import os
import json
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from src.hybrid_extractor import HybridExtractor

app = Flask(__name__)

# Config
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Initialize Extractor
print("⏳ Initializing Extractor...")
extractor = HybridExtractor()
print("✅ Extractor Ready!")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Run Extraction
            result = extractor.extract_from_image(filepath)
            
            # Clean up uploaded file (optional, keeping it for now might be useful for debug)
            # os.remove(filepath)
            
            return jsonify(result)
        except Exception as e:
            print(f"❌ Error processing file: {e}")
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
