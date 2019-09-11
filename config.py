import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(basedir,'.env'))

class Config():
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/Users/hui/Documents/Scripts/ngs_server/app/upload/cache'

    ALLOWED_EXTENSIONS = eval(os.environ.get('ALLOWED_EXTENSIONS')) or {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','csv','sql'}
    PAGE_LIMIT = int(os.environ.get('PAGE_LIMIT') or 10)

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 8025)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['rocksnow1942@gmail.com']
