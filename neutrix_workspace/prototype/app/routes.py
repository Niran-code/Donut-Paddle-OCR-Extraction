from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import logging
from pipeline import HybridExtractorPipeline
from utils.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

bp = Blueprint('routes', __name__)

# Initialize singletons
extractor = None
pdf_processor = None

@bp.record_once
def register(state):
    global extractor, pdf_processor
    logger.info("⏳ Initializing Extractor Pipeline inside routes...")
    # NOTE: In production, consider lazy loading or moving this outside request threads.
    extractor = HybridExtractorPipeline(use_donut=True)
    pdf_processor = PDFProcessor()
    logger.info("✅ Extractor Pipeline Ready!")


@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/process', methods=['POST'])
def process_file():
    """
    Synchronous Document Extraction
    Uploads an image or PDF identity document and synchronously processes it. 
    Not recommended for large PDFs in production.
    ---
    tags:
      - Synchronous Extraction
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: The image or PDF file to process
    responses:
      200:
        description: A JSON dictionary of the extracted Pydantic schema
      400:
        description: Bad request (missing file)
      500:
        description: Internal server error or ML inference failure
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            if filename.lower().endswith(".pdf"):
                logger.info(f"PDF detected: {filename}. Converting pages...")
                _ = pdf_processor.extract_structure_docling(filepath)
                img_paths = pdf_processor.extract_images_from_pdf(filepath)
                if not img_paths:
                    return jsonify({"error": "Failed to parse PDF pages."}), 500
                process_target = img_paths[0]
            else:
                process_target = filepath
                
            result = extractor.process_file(process_target)
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ Error processing file: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@bp.route('/api/v1/process_async', methods=['POST'])
def process_file_async():
    """
    Asynchronous Document Extraction
    Uploads an image or PDF and queues it for background Celery processing.
    Returns a task_id immediately.
    ---
    tags:
      - Asynchronous Tasks
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: The document to process
    responses:
      202:
        description: Processing started successfully, returns task_id
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Dispatch to celery
        try:
             from app.tasks import process_document_async
             task = process_document_async.delay(filepath, filename)
             return jsonify({
                 "task_id": task.id,
                 "status": "Processing Started"
             }), 202
        except Exception as e:
             logger.error(f"Failed to start async task: {e}")
             return jsonify({"error": "Failed to start background task"}), 500

@bp.route('/api/v1/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    Get Asynchronous Task Status
    Poll this endpoint using the task_id to get processing completion status.
    ---
    tags:
      - Asynchronous Tasks
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: The task UUID returned by /process_async
    responses:
      200:
        description: The current state of the job (PENDING, PROCESSING, SUCCESS, FAILURE)
    """
    from app.tasks import process_document_async
    task = process_document_async.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state == 'PROCESSING':
        # Custom state defined in tasks.py
        response = {
            'state': task.state,
            'status': task.info.get('status', 'Processing...')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.info # The JSON result
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'error': str(task.info)
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }
        
    return jsonify(response)
