from app import db
from flask import render_template, flash, redirect,url_for,request,current_app
from flask_login import current_user,login_required
from datetime import datetime
from app.ppt import bp
from app.models import Selection, Rounds, models_table_name_dictionary , SeqRound
from flask import g
from app.ppt.forms import SearchNGSForm, SearchInventoryForm, TestForm
from urllib.parse import urlparse
from app.utils.ngs_util import pagination_gaps,reverse_comp,validate_sequence
from sqlalchemy import or_

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('ppt/index.html',title='PPT')

