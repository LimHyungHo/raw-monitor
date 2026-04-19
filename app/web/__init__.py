from flask import Flask

from app.config.settings import settings


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = settings.SECRET_KEY

    from app.web.routes import web_bp

    app.register_blueprint(web_bp)
    return app
