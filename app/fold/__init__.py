from flask import Blueprint

bp = Blueprint('fold', __name__,)  # template_folder='templates'

from app.fold import routes
