import io,os
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
from app.main.routes import privilege_required
from app.utils.animal_data.animal import Experiment

@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('apps/index.html',title='Apps Page')


@bp.route('/simuojo', methods=['GET', 'POST'])
@login_required
def simuojo():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/simuojo',session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script, title='Simuojo')

@bp.route('/simuojo/static/<path:filename>', methods=['GET'])
def simjojo_static_image(filename):
    return redirect(url_for("static",filename="simuojo/"+filename))
    
@bp.route('/foldojo', methods=['GET', 'POST'])
@login_required
def foldojo():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/foldojo',
                            session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script, title='Foldojo')


@bp.route('/foldojo/static/cache/<path:filename>', methods=['GET'])
def foldojo_images(filename):
    return send_from_directory(current_app.config['FOLDOJO_FOLDER'], filename=filename)


@bp.route('/plojo', methods=['GET', 'POST'])
@login_required
def plojo():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/plojo',session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script,title='Plojo-Curve Fitting')


@bp.route('/plojo_nior', methods=['GET', 'POST'])
@login_required
def plojo_nior():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/plojo-nior',
                            session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script, title='Plojo-nior HPLC data')


@bp.route('/plojo_help', methods=['GET', 'POST'])
@login_required
def plojo_help():
    root = urlparse(request.base_url).hostname
    script = server_session(url='http://'+root+':5006/plojo_help',
                            session_id=generate_session_id())
    return render_template('apps/simuojo.html', script=script, title='Plojo Help')


@bp.route('/plojo_help/static/<path:filename>', methods=['GET'])
def plojo_help_static_image(filename):
    return redirect(url_for("static", filename="plojo_help/"+filename), )


@bp.route('/mw_calculator', methods=['GET', 'POST'])
@login_required
def mw_calculator():
    
    return render_template('apps/mw_calc.html', title='M.W. calculator')



@bp.route('/animal_data', methods=['GET', 'POST'])
@login_required
@privilege_required('manager')
def animal_data():
    data_path = current_app.config['ANIMAL_DATA_PATH']
    filelist = os.listdir(data_path)
    experimentlist = [i.replace('.json','') for i in filelist if i.endswith('.json')]
    for i in filelist:
        if os.path.isdir(os.path.join(data_path, i)) and (i not in experimentlist):
            try:
                Experiment(os.path.join(data_path, i))
                experimentlist.append(i)
            except Exception as e:
                flash('Experiment {} cannot be loaded. Reason:{}'.format(i,e), 'warning')
        

    return render_template('apps/animal/animal_data.html', title= "Animal Data Viewer",experiment_list=experimentlist)


@bp.route('/animal_data_form', methods=['POST'])
@login_required
def animal_data_form():
    data_path = current_app.config['ANIMAL_DATA_PATH']
    data = {item['name']: item['value'] for item in request.json}
    
    try:
        exp = Experiment.load_json(os.path.join(data_path,data['exp']+'.json'))
        exp.update()
        render_kw = exp.render_form_kw(data)
    except Exception as e:
        render_kw={}
    form = render_template('apps/animal/animal_data_form.html', **render_kw)
    title = f"{render_kw.get('animal')}-{render_kw.get('eye')}-{render_kw.get('measure')}-{render_kw.get('day')}"
    return jsonify(form=form,title=title)


@bp.route('/animal_data_figure', methods=['POST'])
@login_required
def animal_data_figure():
    data_path = current_app.config['ANIMAL_DATA_PATH']
    data = {item['name']: item['value'] for item in request.json}
    try:
        exp = Experiment.load_json(
            os.path.join(data_path, data['exp']+'.json'))
        figure_list = exp.render_figure_kw(data)
        note = exp.data.get(data['animal'], {}).get(data['eye'], {}).get('note', '')
    except Exception as e:
        figure_list = {}
        note=''
    html = render_template('apps/animal/animal_data_figure.html', figure_list = figure_list)
    return jsonify(html=html, note=note )


@bp.route('/save_animal_data', methods=['POST'])
@login_required
def save_animal_data():
    data_path = current_app.config['ANIMAL_DATA_PATH']
    try:
        data = {item['name']: item['value']
                for item in request.json.get('data')}
        order = [int(i) for i in request.json.get('order')]
        exp = Experiment.load_json(
            os.path.join(data_path, data['exp']+'.json'))
        r=exp.edit_data(data,order)
        exp.save_json()
        messages = [('success',f'<{r}> note was saved.')]
    except Exception as e:
        messages = [('danger',f"Save data failed: {e}")]
    
    return jsonify(html=render_template('flash_messages.html', messages=messages), )

@bp.route('/get_animal_data_figure/<path:filename>', methods=['GET'])
@login_required
def get_animal_data_figure(filename):
    data_path = current_app.config['ANIMAL_DATA_PATH']
    return send_from_directory(data_path, filename, as_attachment=False)
