from flask import Flask
from routes import setup_routes
from config import Config
from celery_app import celery 
import tasks


def create_app():
    app = Flask(__name__, template_folder='templates')
    setup_routes(app)
        
    return app

app = create_app()


if __name__ == "__main__":
    Config.setup_logging()
    app.run(host=Config.HOST, port=Config.PORT)