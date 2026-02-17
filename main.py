from flask import Flask
from app.webhook.publish_event import meli_publish
from app.webhook.selling_event import meli_sell

def create_app():
    app = Flask(__name__)
    app.register_blueprint(meli_publish)
    app.register_blueprint(meli_sell)
    return app

app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=True)