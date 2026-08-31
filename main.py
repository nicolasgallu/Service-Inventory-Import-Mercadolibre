from flask import Flask
from app.api.publish_event import publications
from app.webhook.selling_event import meli_sell

def create_app():
    app = Flask(__name__)
    app.register_blueprint(publications)
    app.register_blueprint(meli_sell)
    return app

app = create_app()