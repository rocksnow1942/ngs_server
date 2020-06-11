import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(basedir,'.env'))

class Config():
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/Users/hui/Documents/Scripts/ngs_server/app/upload/cache'
    ANALYSIS_FOLDER = os.environ.get(
        'ANALYSIS_FOLDER') or '/Users/hui/Documents/Scripts/ngs_server/app/upload/cache/ANALYSIS_FOLDER'

    ALLOWED_EXTENSIONS = eval(os.environ.get('ALLOWED_EXTENSIONS')) or {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','csv','sql'}
    PAGE_LIMIT = int(os.environ.get('PAGE_LIMIT') or 10)

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL') or None
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 8025)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['rocksnow1942@gmail.com']
    FOLDOJO_FOLDER = os.environ.get('FOLDOJO_FOLDER') or None

    PPT_SOURCE_FOLDER = os.environ.get('PPT_SOURCE_FOLDER') or None
    PPT_TARGET_FOLDER = os.environ.get('PPT_TARGET_FOLDER') or None
    PPT_LOG_FILE = os.environ.get('PPT_LOG_FILE') or None

    APP_ERROR_LOG = os.environ.get('APP_ERROR_LOG') or None

        
    DATABASE_FOLDER = os.environ.get('DATABASE_FOLDER') or '.'

    ANIMAL_DATA_PATH = os.environ.get('ANIMAL_DATA_PATH') or '.'

    # MONGO_URI = os.environ.get('MONGO_URI') or "mongodb://hui:kanghui@pi.hole:27017/test"

    MONGODB_SETTINGS = [{
        'ALIAS':'default',
        'host': os.environ.get(
        'MONGO_DATABSE_1') or "mongodb://hui:kanghui@pi.hole:27017/test"},
        { 
            'ALIAS': 'echem',
            'host': os.environ.get(
            'MONGO_DATABSE_2') or "mongodb://buglogger:buglogger@pi.hole:27017/buglogger"},
        ]
