from flask import Blueprint

bp = Blueprint('ngs', __name__,)  # template_folder='templates'

from app.ngs import routes
