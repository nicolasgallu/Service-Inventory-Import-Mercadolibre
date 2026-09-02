from flask import Flask
from app.api.publish_event import publications
from app.webhook.selling_event import sells

def create_app():
    app = Flask(__name__)
    app.register_blueprint(publications)
    app.register_blueprint(sells)
    return app

app = create_app()