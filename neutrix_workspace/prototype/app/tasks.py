from celery import shared_task
from pipeline import HybridExtractorPipeline
from utils.pdf_processor import PDFProcessor
import os
import logging

logger = logging.getLogger(__name__)

# Lazy initialization in worker
_extractor = None
_pdf_processor = None

def get_extractor():
    global _extractor
    if _extractor is None:
        logger.info("Initializing HybridExtractorPipeline in Celery Worker...")
        _extractor = HybridExtractorPipeline(use_donut=True)
    return _extractor

def get_pdf_processor():
    global _pdf_processor
    if _pdf_processor is None:
        logger.info("Initializing PDFProcessor in Celery Worker...")
        _pdf_processor = PDFProcessor()
    return _pdf_processor

@shared_task(bind=True)
def process_document_async(self, filepath: str, filename: str):
    logger.info(f"Task {self.request.id}: Starting background processing for {filename}")
    
    # Update state
    self.update_state(state='PROCESSING', meta={'status': 'Starting extraction...'})
    
    extractor = get_extractor()
    pdf_processor = get_pdf_processor()
    
    try:
        if filename.lower().endswith(".pdf"):
            logger.info(f"Task {self.request.id}: PDF detected. Converting pages...")
            self.update_state(state='PROCESSING', meta={'status': 'Converting PDF to images...'})
            
            _ = pdf_processor.extract_structure_docling(filepath)
            img_paths = pdf_processor.extract_images_from_pdf(filepath)
            if not img_paths:
                raise Exception("Failed to parse PDF pages.")
            process_target = img_paths[0]
        else:
            process_target = filepath
            
        self.update_state(state='PROCESSING', meta={'status': 'Running ML Pipeline...'})
        result = extractor.process_file(process_target)
        
        logger.info(f"Task {self.request.id}: Processing complete.")
        return result
        
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error processing file: {e}", exc_info=True)
        raise e
