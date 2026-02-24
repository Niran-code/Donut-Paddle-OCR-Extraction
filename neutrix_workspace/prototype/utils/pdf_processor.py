import os
import fitz  # PyMuPDF
import logging
from typing import List, Tuple, Optional
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, output_dir: str = "uploads"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        if DOCLING_AVAILABLE:
            self.converter = DocumentConverter()
            logger.info("Docling initialized for PDF document processing.")
        else:
            self.converter = None
            logger.warning("Docling not available. Falling back to simple PyMuPDF extraction.")

    def extract_images_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Converts a PDF into a list of image paths (one per page).
        Requires PyMuPDF.
        """
        image_paths = []
        try:
            doc = fitz.open(pdf_path)
            base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=300) # High quality for OCR
                
                output_path = os.path.join(self.output_dir, f"{base_filename}_page_{page_num+1}.jpg")
                pix.save(output_path)
                image_paths.append(output_path)
                
            doc.close()
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            
        return image_paths

    def extract_structure_docling(self, pdf_path: str) -> Optional[dict]:
        """
        Extract structured layout logic using Docling.
        This allows for block-level analysis if needed before OCR.
        """
        if not self.converter:
            return None
            
        try:
             result = self.converter.convert(pdf_path)
             # Export to JSON
             return result.document.export_to_dict()
        except Exception as e:
             logger.error(f"Docling analysis failed for {pdf_path}: {e}")
             return None
