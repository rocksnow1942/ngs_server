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
    data format: {key: index of plojo entry if it is already created, if not created, key = ""
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
    data_key = data.get('key',None)
    filename = data.get('filename','Unknown File')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    chanel = data.get('chanel','Unknown Chanel')
    projectname = data.get('project', None)
    
    if projectname:
        project = Plojo_Project.query.filter(
        Plojo_Project.index.contains(projectname)).first()

        if not project:
            new_project_index = Plojo_Project.next_index(projectname)
            project = Plojo_Project(index=new_project_index,_data="[]")
            db.session.add(project)
            db.session.commit()

        if not data_key:
            note = "Starting File: " + filename
            expdate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            newdata = Plojo_Data(index= Plojo_Data.next_index(),_data="{}")
            newdata.data = dict( note=note, name=chanel+" | "+date, author='Script upload', concentration=[], signal=[],
                                date=expdate.strftime("%Y%m%d"), assay_type="echem", fit_method='none',)
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
