from alchemical.flask import Alchemical
from apifairy import APIFairy
from flask import Flask
from flask import redirect
from flask import request
from flask import url_for
from flask_cors import CORS
from flask_mail import Mail
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate

from config import Config
# import flask_admin

db = Alchemical()
migrate = Migrate()
ma: Marshmallow = Marshmallow()
cors = CORS()
mail = Mail()
apifairy = APIFairy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # extensions
    from api import models
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    if app.config['USE_CORS']:  # pragma: no branch
        cors.init_app(app)
    mail.init_app(app)
    apifairy.init_app(app)

    # blueprints
    from api.errors import errors
    app.register_blueprint(errors)
    from api.tokens import tokens
    app.register_blueprint(tokens, url_prefix='/api')
    from api.users import users
    app.register_blueprint(users, url_prefix='/api')
    from api.accounts import accounts
    app.register_blueprint(accounts, url_prefix='/api')
    from api.mission import missions
    app.register_blueprint(missions, url_prefix='/api')
    from api.admin import admin
    app.register_blueprint(admin, url_prefix='/api/admin')

    # admin.add_view(ModelView(models.User, db.session))
    # from api.posts import posts
    # app.register_blueprint(posts, url_prefix='/api')
    from api.cmd import cmd
    app.register_blueprint(cmd)

    # define the shell context
    @app.shell_context_processor
    def shell_context():  # pragma: no cover
        ctx = {'db': db}
        for attr in dir(models):
            model = getattr(models, attr)
            if hasattr(model, '__bases__') and \
                    db.Model in getattr(model, '__bases__'):
                ctx[attr] = model
        return ctx

    @app.route('/')
    def index():  # pragma: no cover
        return redirect(url_for('apifairy.docs'))

    @app.after_request
    def after_request(response):
        # Werkzeu sometimes does not flush the request body so we do it here
        request.get_data()
        return response

    return app
