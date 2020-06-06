from app import db
from flask import current_app,render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import current_user,login_required
from app.API import bp
from app.models import AccessLog,Selection, Rounds, models_table_name_dictionary, SeqRound, Project, PPT, Slide, Task, NGSSampleGroup, Analysis
from app.plojo_models import Plojo_Data, Plojo_Project
from datetime import datetime

@bp.route('/testapi', methods=['POST','GET'])
def testapi():
    data = request.json
    print(data)
    return jsonify(data)

@bp.route('/add_echem_pstrace',methods=['POST'])
def add_echem_pstrace():
    """
    add echem pstrace to plojo data base. 
    data format: {md5: md5 of the first pss file, 
                key: index of plojo entry if it is already created,
                filename: file path of the pss file,
                date: date of the first pss file, read from corresponding psmethod file,
                time: the time point of this scan, in minutes,
                potential: voltage data,
                amp: amperage data,}
    the data is for one scan, 
    if key is provided, will append data to the existing trace,
    if key is not provided, will create a new plojo entry, but will check md5 first to see if 
    this trace is already added. and return the current length of trace. 
    """
    data = request.json 
    md5 = data.get('md5',None)
    data_key = data.get('key',None)
    filename = data.get('filename','Unknown')
    date = data.get('date', datetime.now().strftime('%Y%m%d %H:%M'))
    if md5 or data_key:
        projectname = data.get('project', 'Echem_Scan')
        project = Plojo_Project.query.filter(
        Plojo_Project.index.contains(projectname)).first()

        if not project:
            new_project_index = Plojo_Project.next_index(projectname)
            project = Plojo_Project(index=new_project_index,_data="[]")
            db.session.add(project)
            db.session.commit()

        if not data_key:
            plojo_data = Plojo_Data.query.filter(Plojo_Data._data.contains(md5)).all()
            if len(plojo_data) > 1:
                existed_data = [i.index for i in plojo_data]
                return f"Error-Filename: {filename}, md5 {md5} have more than one existance. In {','.join(existed_data)}"
            elif len(plojo_data) == 1:
                return f"Exist-{plojo_data[0].index}-{len(plojo_data[0].data.get('signal', []))}"
            else:
                note = "Starting File: " + filename
                newdata = Plojo_Data(index= Plojo_Data.next_index(),_data="{}")
                newdata.data = dict(flag=md5, note=note, name=date, author='Script upload', concentration=[], signal=[],
                                    date=datetime.now().strftime('%Y%m%d'), assay_type="echem", fit_method='none',)
                db.session.add(newdata)
                project.data = project.data + [newdata.index]
                db.session.commit()
                current_app.task_queue.enqueue(
                    'app.tasks.echem_fitting.add_echem_pstrace', newdata.index, data, job_timeout=3600)
                return f"Add-{newdata.index}"
        else:
            plojo_data = Plojo_Data.query.get(data_key) 
            if plojo_data:
                current_app.task_queue.enqueue(
                    'app.tasks.echem_fitting.add_echem_pstrace',data_key,data, job_timeout=3600) 
                return "OK"
            else:
                return f"Error-Invalid key: {data_key}, filename: {filename}"
    return jsonify("Error-Invalid request")

@bp.route('/get_plojo_data', methods=['GET'])
def get_plojo_data():
    """
    get a plojo data dictionary 
    request format: json={keys:['ams124','ams123'],project:'7-Echem_Scan'}
    """
    keys = request.json.get('keys',None)
    project = request.json.get('project',None)
    if keys:
        res = Plojo_Data.query.filter(Plojo_Data.index.in_(keys)).all()
        return jsonify({i.index:i.data for i in res})
    if project:
        res = Plojo_Project.query.filter(
            Plojo_Project.index.contains(project)).all()
        return jsonify([i.data for i in res])
    return jsonify("Error-Invalid request")
