import io
from app import db
from matplotlib.backends.backend_svg import FigureCanvasSVG
from flask import render_template, flash, redirect, url_for, request, current_app, abort, jsonify, Response
from flask_login import current_user,login_required
from datetime import datetime
from app.fold import bp
from app.models import Selection,Rounds,Primers,Sequence,SeqRound,NGSSampleGroup,NGSSample,KnownSequence
from sqlalchemy.exc import IntegrityError
from app.models import models_table_name_dictionary


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('fold/index.html',title='NGS')
