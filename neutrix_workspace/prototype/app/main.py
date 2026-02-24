from flask import Flask
import os
import logging
from celery import Celery
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
                
    celery.Task = ContextTask
    return celery

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # Swagger UI config
    app.config['SWAGGER'] = {
        'title': 'Hybrid Document Extraction API',
        'uiversion': 3
    }
    from flasgger import Swagger
    Swagger(app)
    
    # Config
    UPLOAD_FOLDER = 'uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    
    # Celery Config
    app.config.update(
        CELERY_BROKER_URL=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        CELERY_RESULT_BACKEND=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    
    # Initialize Celery
    app.celery = make_celery(app)
    
    # Import specific routes
    from . import routes
    app.register_blueprint(routes.bp)
    
    return app
