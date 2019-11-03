from flask import Blueprint

bp=Blueprint('ppt',__name__)

from app.ppt import routes
