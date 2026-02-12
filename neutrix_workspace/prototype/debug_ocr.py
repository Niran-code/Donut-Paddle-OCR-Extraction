from paddleocr import PaddleOCR
import os

def test_ocr():
    image_path = 'data/aadhar_sample.jpg'
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return

    print(f"Testing OCR on {image_path}")

    try:
        ocr = PaddleOCR(use_angle_cls=False, lang='en', enable_mkldnn=False,
                        text_det_limit_side_len=960) 
        
        result = ocr.ocr(image_path)
        
        print("\n--- Deep Inspection ---")
        print(f"Result Type: {type(result)}")
        print(f"Result Length: {len(result) if result else 'None'}")
        print(f"Result Raw: {result}")

        if result:
            for i, item in enumerate(result):
                print(f"Item {i} Type: {type(item)}")
                print(f"Item {i} Content: {item}")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ocr()
