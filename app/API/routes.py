from app import db,mongo
from flask import current_app,render_template, flash, redirect, url_for, request, current_app, jsonify,abort
# from flask_login import current_user,login_required
from app.API import bp
# from app.models import AccessLog,Selection, Rounds, models_table_name_dictionary, SeqRound, Project, PPT, Slide, Task, NGSSampleGroup, Analysis
from app.plojo_models import Plojo_Data, Plojo_Project
from datetime import datetime
from app.tasks.myfit import myfitpeak
from app.mongomodels import Experiment,Project,EchemData
from dateutil import parser
from bson import ObjectId
import time


@bp.route('/testapi', methods=['PUT'])
def testapi():
    data = request.json
    print(data)
    time.sleep(600)
    return
    # if request.method == 'GET':
    #     return render_template('sudoku/index.html')
    


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
    on my localhost, the latency of fitting is about 0.03 seconds for 300point data. 
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
        
        potential = data.get('potential', None)
        amp = data.get('amp', None)
        time = round(float(data.get('time', 0)), 6)
        fittingerror = ""
        if potential and amp:
            try:
                res = myfitpeak(potential, amp)
                peakcurrent = round(float(res['pc']), 6)
            except Exception as e:
                fittingerror = str(e)
                peakcurrent = -100  # to indicate fitting error
        else:
            peakcurrent = -50  # to indicate missing value

        if fittingerror:
            fittingerror = "Fitting Error " + \
                str(fittingerror) + ' ON ' + filename + \
                ":::" 

        if not data_key:
            note = fittingerror + "Starting File: " + filename
            
            expdate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            newdata = Plojo_Data(index= Plojo_Data.next_index(),_data="{}")
            
            newdata.data = dict(note=note, name=chanel+" | "+date, author='Script upload', concentration=[time], signal=[peakcurrent],
                                date=expdate.strftime("%Y%m%d"), assay_type="echem", fit_method='none',)
            
            db.session.add(newdata)
            project.data = project.data + [newdata.index]
            db.session.commit()
           
            return f"Add-{newdata.index}"
        else:
            plojo_data = Plojo_Data.query.get(data_key) 
            if plojo_data:
                plojodata_data = plojo_data.data

                plojodata_data['note'] =fittingerror + plojodata_data.get('note', 'No Note').split(
                    '||')[0].strip() + " || " + f"Ending File: {filename}"

                for i, j in zip(['concentration', 'signal'], [time, peakcurrent]):
                    # plojodata_data[i] = plojodata_data.get(i, [])
                    plojodata_data[i].append(j)
                plojo_data.data = plojodata_data
                db.session.commit()
               
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


# @bp.route('/upsert_echem_experiment',methods=['POST'])
# def add_echem_data():
#     """
#     add echem data to mongodb collection. 
#     json format:
#     {
#         experiment:{} # add new experiment , refer to create_echem_experiment for formatting
#         project: {} # add new project , refer to create_echem_project for formatting
#         rawdata: {} # add to EchemData, refer to create_echem_rawdata for formatting
#     }
#     """
#     package = request.json
#     response = {}
#     for key, payload in package.items():
#         try:
#             if key == 'experiment':
#                 res = create_echem_experiment(payload)
#             elif key == 'project':
#                 res = create_echem_project(payload)
#             elif key == 'rawdata':
#                 res = create_echem_rawdata(payload)
#             else:
#                 res = {key: {'status': 'error', 'err': 'Error -  invalid key.'}}
#         except Exception as e:
#             res = {key: {'status': 'error', 'err': str(e)}}
#         response.update(res)
#     return response

def get_Unassigned_Project():
    project = Project.objects(name='Unassigned experiments').first()
    if not project:
        project = Project(name='Unassigned experiments',
                        desc="To store experiments that doesn't belong to any project.").save()
    return project

def get_Unassigned_Experiment():
    exp = Experiment.objects(name='Unassigned Raw Data').first()
    if not exp:
        project = get_Unassigned_Project()
        exp = Experiment(name='Unassigned Raw Data', author='Unknown', note="", project = project,
                        desc="Data that don't belong to any other experiments.").save()
    return exp


@bp.route('/upsert_echem_experiment', methods=['POST'])
def upsert_echem_experiment():
    """create a new echem experiment
    payload format:
    {   
        id: string, if id is provided, will update the experiment with the same id.
        name : string, 
        author : string, 
        note: string, 
        desc: string, 
        project: string, id of the project it need to add to.
        if other key is passed in, will use it. 
    }
    """
    payload = request.json
    try:
        id = payload.pop('id',None)
        project = payload.get('project', None)
        if project:
            payload.update(project=ObjectId(project))
        
        if id==None:
            if not project:
                project = get_Unassigned_Project()
                payload.update(project=project)
            exp = Experiment(**payload)
            exp.save()
            id = exp.id
        else:
            Experiment.objects(id=id).update_one(**payload)
        return  {'status': 'ok', 'id': str(id)}
    except Exception as e:
        return {'status': 'error', 'err': str(e)}


@bp.route('/upsert_echem_project', methods=['POST'])
def upsert_echem_project():
    """
    create echemproject 
    payload format:
    {   
        id: string of project id. if id is provided, will update the existing document.
        name: string, 
        desc: string ,
        other keys will be saved.
    }
    """
    payload = request.json
    try:
        id = payload.pop('id',None)
        if id == None:
            project = Project(**payload).save()
            id = project.id
        else:
            Project.objects(id=id).update_one(**payload)
        return {'status':'ok','id':str(id)}
    except Exception as e:
        return {'status':'error','err':str(e)}


@bp.route('/upsert_echem_rawdata', methods=['POST'])
def upsert_echem_rawdata():
    """
    raw data format:
    id: if no id, then create new EchemData. if have id, then append data or update data.
    dtype: also required, this determine how the payload is read.
    name: string, name of echem data. 
    desc: string, description of data. 
    author: string , author of data
    exp: id of experiment, if not, will create a new experiment to add data. 
    data: data package 
    dtype=='covid-trace' payload data format:
    {
        time: [timestamp ... ]
        rawdata: [[v,a]...]
        fit: [{...},{...}...]
    }
    dtype=='device-trace'
    data is the same, 
    _id: Object ID to use for store data. 
    meta : {method,deltaT,temp,name,exp,desc,device,created}
    status: 'ok' or abort
    data: {'time': [timepoint in minutes], 'rawdata': [[v,a]...], 'fit': [{fitresult}...], 'temp':[]} 
    result: posotive or negative
    """
    action = request.json.pop('action',None)
    payload = request.json

    data = payload.pop('data',None)

    id = payload.get('id',None)
    # if no data provided and id is provided, will update other fields.
    
    # return error if dtype is not supported by EchemData class.
    dtype = payload.get('dtype', None)
    if dtype not in EchemData.DTYPE:
        return  {'status': 'error', 'response': 'invalid dtype'}
    
    # place holder for generate echem data. 
    echemdata = None 
    # create a new EchemData document if id is not provided.
    exp = payload.get('exp', "").strip()

    if dtype == 'device-trace':
        exp = payload.get('meta',{}).pop('exp',"Unknown Device Exp")
        payload.update(author = 'Device') # payload author is used for experiment author
    if exp:
        # check if exp is an ObjectId 
        if ObjectId.is_valid(exp):
            payload.update(exp=ObjectId(exp))
        else: # if exp is a normal string, 
            tempExp = Experiment.objects(name=exp).first()
            if not tempExp:
                project = get_Unassigned_Project()
                tempExp = Experiment(name=exp,author=payload.get('author','Unknown'),project=project)
                tempExp.save()
            payload.update(exp=tempExp) 
    else:
        exp = get_Unassigned_Experiment()
        payload.update(exp=exp)

    # device-trace update directly.
    if dtype=='device-trace':
        meta = payload.get('meta',{})
        name = meta.pop('name','Device No Name')
        desc = meta.pop('desc','')
        author = meta.pop('device',"Unknown Device") # device author is device ID.
        created = parser.parse(meta.pop('created',"2000-01-01"))
        meta.update(result=payload.get('result',""))
        data.update(meta=meta)
        newdata = EchemData(id=payload['_id'],dtype=dtype,name=name,desc=desc,exp=payload['exp'],
                    author=author, data=data,created=created)
        try:
            newdata.save()
            return {'status': 'ok', 'id':  str(newdata.id)}
        except Exception as e:
            return {'status':'error','error':str(e)}


    if (not data) and id: # if no data and id, then update meta info. 
        EchemData.objects(id=id).update_one(**payload)
        return  {'status': 'ok', 'response': 'updated raw data meta info', 'id':id}


    if not id:
        # if id for echem data is not provided, need to put it in new experiment.
        echemdata = EchemData(**payload)
        echemdata.save()
        id = echemdata.id

    # parse the data according to dtype
    if dtype == 'covid-trace':
        updatedict = payload
        try:
            t = [parser.parse(i) for i in data['time']]
            rawdata = data['rawdata']
            # fitres = [myfitpeak(v, a) for v, a in rawdata]
            fitres = data['fit']
            updatedict["push_all__data__time"] = t
            updatedict["push_all__data__rawdata"] = rawdata
            updatedict["push_all__data__fit"] = fitres
            EchemData.objects(id=id).update_one(**updatedict)
            return  {'status': 'ok', 'id':  str(id)}
        except Exception as e:
            # roll back:
            if echemdata: echemdata.delete()
            return   {'status': 'error', 'response': str(e)}

    return  {'status': 'error', 'response': "weird, nobody can reach here."}

@bp.route('/delete_echem_data', methods=['DELETE'])
def delete_echem_data():
    "delete an item from mongodb, format: {id: , type: }"
    data = request.json 
    id = data.get('id',None)
    ob = data.get('type',None)
    model = {'Experiment':Experiment,'Project':Project,'EchemData':EchemData}
    try:
        model[ob].objects(id=id).delete()
        return {'status':'ok'}
    except Exception as e:
        return {'status':'error','err':str(e)}


@bp.route('/echem_main',methods=['DELETE','POST','GET'])
def echem_main():
    "main gate for all data activities"
    method = request.method 
    action = request.json.pop('action',None)
    if method == 'DELETE':
        return delete_echem_data()
    elif method == 'POST':
        if action == 'upsert_rawdata':
            return upsert_echem_rawdata()
    elif method == 'GET':
        return get_echem_data()

    return abort(404)


@bp.route('/get_echem_data',methods=['GET'])
def get_echem_data():
    "return data."
    data = request.json 

    
    print(data,'get_echem_data')
    res = EchemData.objects(id=data['id']) 

    return jsonify(res)
 