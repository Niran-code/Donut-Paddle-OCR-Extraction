from transformers import AutoProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image
import re
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DonutEngine:
    def __init__(self, model_name: str = "naver-clova-ix/donut-base-finetuned-docvqa"):
        self.model_name = model_name
        self.processor = None
        self.model = None
        self.device = None

    def _get_model(self):
        if self.model is None or self.processor is None:
            try:
                logger.info("⏳ Loading Donut Processor & Model (Lazy Load)...")
                self.processor = AutoProcessor.from_pretrained(self.model_name)
                self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model.to(self.device)
                self.model.eval()
                logger.info(f"✅ Donut ready on {self.device}.")
            except Exception as e:
                logger.error(f"❌ Donut initialization failed: {e}")
                raise
        return self.model, self.processor, self.device

    def process_image(self, image_path: str, prompt: str = "<s_docvqa><s_question>extract all fields</s_question><s_answer>") -> Dict[str, Any]:
        """
        Runs Donut layout-based extraction. 
        Returns parsed JSON dict or empty dict on failure.
        """
        try:
            model, processor, device = self._get_model()
            image = Image.open(image_path).convert("RGB")
            
            pixel_values = processor(image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(device)

            decoder_input_ids = processor.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids
            decoder_input_ids = decoder_input_ids.to(device)
            
            outputs = model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=model.decoder.config.max_position_embeddings,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
                bad_words_ids=[[processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
                output_scores=True
            )
            
            sequence = processor.batch_decode(outputs.sequences)[0]
            sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
            # Remove prompt
            sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  

            return processor.token2json(sequence)

        except Exception as e:
            logger.error(f"Donut Extraction Failed: {e}")
            return {}
