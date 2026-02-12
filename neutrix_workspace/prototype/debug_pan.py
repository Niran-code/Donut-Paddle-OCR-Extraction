from src.hybrid_extractor import HybridExtractor
import os

def debug_pan():
    extractor = HybridExtractor()
    image_path = "uploads/pan_sample.jpg"
    
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return

    print(f"Processing {image_path}...")
    
    # Run Preprocessing
    proc_img = extractor._preprocess_image(image_path)
    print(f"Preprocessed image type: {proc_img}")
    
    # Run OCR
    try:
        ocr_result = extractor.ocr.ocr(proc_img)
    except Exception as e:
        print(f"OCR Failed: {e}")
        ocr_result = []
    
    print(f"OCR Result Type: {type(ocr_result)}")
    if isinstance(ocr_result, list):
        print(f"OCR Result Length: {len(ocr_result)}")
        if len(ocr_result) > 0:
             print(f"Item 0 Type: {type(ocr_result[0])}")
             print(f"Item 0 Dir: {dir(ocr_result[0])}")
             if hasattr(ocr_result[0], 'rec_texts'):
                  print("Found rec_texts in Item 0")

    lines = []
    if isinstance(ocr_result, list) and len(ocr_result) > 0:
        result_obj = ocr_result[0]
        # Try accessing as dict/Item first
        try:
             # PaddleX OCRResult often behaves like a dict
             if 'rec_texts' in result_obj:
                 rec_texts = result_obj['rec_texts']
                 rec_scores = result_obj['rec_scores'] if 'rec_scores' in result_obj else []
                 
                 for i, text in enumerate(rec_texts):
                    conf = rec_scores[i] if i < len(rec_scores) else 0.0
                    print(f"RAW OCR LINE: '{text}' (Conf: {conf:.2f})")
                    lines.append(text)
             elif hasattr(result_obj, 'rec_texts'):
                 # Attribute access
                 rec_texts = result_obj.rec_texts
                 # ...
        except Exception as e:
             print(f"Error accessing result_obj: {e}")
             
        # Legacy/Standard PaddleOCR format fallback
        if not lines and isinstance(result_obj, list):
             for line in result_obj:
                if len(line) >= 2 and isinstance(line[1], (list, tuple)):
                    text = line[1][0]
                    confidence = line[1][1]
                    print(f"RAW OCR LINE: '{text}' (Conf: {confidence:.2f})")
                    lines.append(text)
            
    print("\n--- Parsing ---")
    data = extractor._parse_pan("", lines)
    print("Parsed Data:", data)

if __name__ == "__main__":
    debug_pan()
