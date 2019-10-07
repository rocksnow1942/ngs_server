from flask import Flask
from flask_migrate import Migrate
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from logging.handlers import SMTPHandler, RotatingFileHandler
import logging
import os
from redis import Redis
import rq
from elasticsearch import Elasticsearch

db = SQLAlchemy()
migrate=Migrate()
bootstrap = Bootstrap()
mail = Mail()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'

def create_app(config_class = Config,keeplog=True):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app,db)
    bootstrap.init_app(app)
    login.init_app(app)
    mail.init_app(app)

    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('ngs-server-tasks', connection=app.redis)

    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp,url_prefix='/auth')

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.APPS import bp as apps_bp
    app.register_blueprint(apps_bp, url_prefix='/apps')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp,url_prefix='/admin')

    from app.ngs import bp as ngs_bp
    app.register_blueprint(ngs_bp, url_prefix='/ngs')

    from app.ppt import bp as ppt_bp
    app.register_blueprint(ppt_bp, url_prefix='/ppt')

    from app.upload import bp as upload_bp
    app.register_blueprint(upload_bp,url_prefix='/upload')
   
    if (not app.debug) and (not app.testing) and keeplog:
        if not os.path.exists('logs'):
            os.mkdir('logs')
           
        file_handler = RotatingFileHandler('logs/ngs_server.log',maxBytes=10240,backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.ERROR)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.ERROR)
        app.logger.info('ngs_server startup')

    return app



from app import models,plojo_models

