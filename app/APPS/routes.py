import io
from app import db
from matplotlib.backends.backend_svg import FigureCanvasSVG
from flask import render_template, flash, redirect, url_for, request, current_app, abort, jsonify, Response, send_from_directory
from flask_login import current_user,login_required
from datetime import datetime
from app.APPS import bp
from app.models import Selection,Rounds,Primers,Sequence,SeqRound,NGSSampleGroup,NGSSample,KnownSequence
from sqlalchemy.exc import IntegrityError
from app.models import models_table_name_dictionary

from bokeh.embed import server_document,server_session
from bokeh.client import pull_session

from bokeh.util.session_id import generate_session_id
from urllib.parse import urlparse


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('apps/index.html',title='NGS')


@bp.route('/simuojo', methods=['GET', 'POST'])
@login_required
def simuojo():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/simuojo',session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script,)

@bp.route('/simuojo/static/<path:filename>', methods=['GET'])
def simjojo_static_image(filename):
    return redirect(url_for("static",filename="simuojo/"+filename))
    
@bp.route('/foldojo', methods=['GET', 'POST'])
@login_required
def foldojo():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/foldojo',
                            session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script)


@bp.route('/foldojo/static/cache/<path:filename>', methods=['GET'])
def foldojo_images(filename):
    return send_from_directory(current_app.config['FOLDOJO_FOLDER'], filename=filename)


@bp.route('/plojo', methods=['GET', 'POST'])
@login_required
def plojo():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/plojo',session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script)


@bp.route('/plojo_nior', methods=['GET', 'POST'])
@login_required
def plojo_nior():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/plojo-nior',
                            session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script)


@bp.route('/plojo_help', methods=['GET', 'POST'])
@login_required
def plojo_help():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/plojo_help',
                            session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script)


@bp.route('/plojo_help/static/<path:filename>', methods=['GET'])
def plojo_help_static_image(filename):
    return redirect(url_for("static", filename="plojo_help/"+filename))


@bp.route('/mw_calculator', methods=['GET', 'POST'])
@login_required
def mw_calculator():
    
    return render_template('apps/mw_calc.html', )
