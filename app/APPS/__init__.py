from flask import Blueprint

bp = Blueprint('apps', __name__,)  # template_folder='templates'

from app.APPS import routes
