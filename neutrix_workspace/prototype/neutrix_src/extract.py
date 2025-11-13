from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
from .utils import (
    clean_donut_output,
    print_boxed,
    validate_and_clean_fields,
    detect_document_type,
)


class DonutExtractor:
    def __init__(self, model_name="naver-clova-ix/donut-base-finetuned-docvqa"):
        print_boxed(f"Loading Donut model ({model_name}) and processor...")
        self.processor = DonutProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        self.model.eval()
        print("✅ Donut model loaded successfully (fine-tuned for document QA)")

    def extract_from_image(self, image_path: str):
        image = Image.open(image_path).convert("RGB")

        # The model was trained on question–answer (DocVQA) tasks,
        # so we use a specific prompt to guide it toward KVP extraction.
        task_prompt = "<s_docvqa><s_question>Extract all key-value pairs from this document</s_question><s_answer>"

        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        decoder_input_ids = self.processor.tokenizer(
            task_prompt, add_special_tokens=False, return_tensors="pt"
        ).input_ids

        with torch.no_grad():
            output_ids = self.model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=768,  # slightly higher limit for longer docs
                num_beams=4,
                early_stopping=True,
            )

        result = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]

        # Step 1️⃣ Clean & parse the raw model output
        data = clean_donut_output(result)

        # Step 2️⃣ Validate & normalize fields using regex logic
        clean_data = validate_and_clean_fields(data)

        # Step 3️⃣ Detect likely document type
        doc_type = detect_document_type(clean_data)
        clean_data["document_type"] = doc_type

        return clean_data
