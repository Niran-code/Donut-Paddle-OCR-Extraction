import os
from dotenv import load_dotenv

# Load any .env variables
load_dotenv()

from app.main import create_app

flask_app = create_app()
celery_app = flask_app.celery

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    flask_app.run(debug=debug_mode, host='0.0.0.0', port=port)
