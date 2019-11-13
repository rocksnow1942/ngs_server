from app import db
from flask import render_template, flash, redirect,url_for,request,current_app,jsonify
from flask_login import current_user,login_required
from app.admin import bp
from app.models import AccessLog,Selection, Rounds, models_table_name_dictionary, SeqRound, Project, PPT, Slide, Task, NGSSampleGroup, Analysis
from datetime import datetime, timedelta
import glob,shutil,os,psutil
from app.utils.common_utils import get_folder_size
from app.main.routes import privilege_required
from flask_user import roles_required

@bp.route('/', methods=['GET', 'POST'])
@login_required
@privilege_required('admin')
def admin():
    return render_template('admin/index.html',title='Admin Page')


@bp.route('/clear_trash', methods=['GET', 'POST'])
def clear_trash():
    """
    clear tasks that are more than a day old.
    delete unused uploaded files, deleted analysis folders
    """
    msg = []
    oldtask = Task.query.filter(Task.date < (
        datetime.now() - timedelta(days=1))).all()
    try:
        for i in oldtask:
            msg.append(f'Deleting task, id:<{i.id}>')
            db.session.delete(i)
        db.session.commit()
        msg.append(f'All trash tasks deleted. Total count: <{len(oldtask)}>')
        flash('Deleted {} tasks.'.format(len(oldtask)),'success')
    except Exception as e:
        flash('Delete Tasks error :<{}>.'.format(e), 'danger')
        msg.append(f'Delete Tasks error. Error : <{e}>')
    # need to delete trash from SQL tasks, and unused analysis folders.
    # clear up file uploads.
    uploadfolder = current_app.config['UPLOAD_FOLDER']
    fastq = glob.glob(uploadfolder+'/*.fastq')
    nsgfiles = [file for i in NGSSampleGroup.query.all() for file in i.files]
    msg.append(f'Total fastq files: {len(fastq)}; total fastq files in use: {len(nsgfiles)}')
    for f in fastq:
        if f not in nsgfiles:
            # delete fastq file
            os.remove(f)
            msg.append('Delete fastq: {}'.format(f))
    
    # clean up analysis files:
    _af = current_app.config['ANALYSIS_FOLDER'] + '/'
    ana_folder = [ _af+ str(i.id) for i in Analysis.query.all()]
    ana_cf = glob.glob(_af+'*')
    for i in ana_cf:
        if i not in ana_folder:
            # delete folder  
            shutil.rmtree(i)
            msg.append('Delete analysis folder: {}'.format(i))
    return render_template('admin/result.html', content=msg)


@bp.route('/reindex_models', methods=['GET', 'POST'])
def reindex_models():
    """
    reindex all the elastic searach models
    """
    msg=[]
    try:
        for k,item in models_table_name_dictionary.items():
            if 'SearchableMixin' in [i.__name__ for i in item.__bases__]:
                item.reindex()
                flash('Reindex <{}>... success.'.format(k), 'success')
                msg.append('Reindex <{}>... success.'.format(k))
    except Exception as e:
        flash(str(e),'danger')
        msg.append(str(e))
        return render_template('admin/result.html', content=['Shit happened.']+msg)
    return render_template('admin/result.html', content=['Success.']+msg)


@bp.route('/clear_ppt_trash', methods=['GET', 'POST'])
def clear_ppt_trash():
    """
    clear empty project, and ppt that not in project and slides.
    """
    msg=[]
    try:
        # clear project 
        projects = [i for i in Project.query.all() if not i.ppts]
        for p in projects:
            db.session.delete(p)
            db.session.commit()
            ss = 'Delete {}... success.'.format(p)
            flash(ss, 'success')
            msg.append(ss)
        # clear PPT
        ppt = PPT.query.filter_by(project_id=None).all()
        for p in ppt:
            for s in p.slides:
                if s.note or s.tag:
                    s.ppt_id=None
            db.session.commit()
            db.session.delete(p)
            db.session.commit()
            ss = 'Delete {}... success.'.format(p)
            flash(ss,'success')
            msg.append(ss)
        # clear Slides
        slides = Slide.query.filter_by(ppt_id=None).all()
        count=0
        for s in slides:
            if s.note or s.tag:
                pass
            else:
                db.session.delete(s)
                count+=1
                db.session.commit()
        if count:
            ss = 'Deleted {} slide pages... success.'.format(count)
            flash(ss, 'success')
            msg.append(ss)
    except Exception as e:
        flash(str(e), 'danger')
        return render_template('admin/result.html', content=['Shit happened.']+msg)
    return render_template('admin/result.html', content=['Success.']+msg)
    

@bp.route('/reindex_ppt', methods=['GET', 'POST'])
def reindex_ppt():
    try:
        # msg = reindex()
        assert 1==0,('error this is not implemented')
    except Exception as e:
        flash(str(e),'danger')
        msg=['This is not implemented yet.']
    return render_template('admin/result.html', content=msg)


@bp.route('/test', methods=['GET', 'POST'])
def test():
    import time
    time.sleep(40)
    msg=['This is a tests']
    return render_template('admin/result.html', content=msg)


@bp.route('/get_system_usage', methods=['POST'])
def get_system_usage():
    cpu = psutil.cpu_percent()
    memory=psutil.virtual_memory().percent
    return jsonify(dict(cpu=min(cpu, 99.9), memory=min(memory,99.9)))


@bp.route('/get_harddrive_usage', methods=['POST'])
def get_harddrive_usage():
    total, used, free = shutil.disk_usage("/")
    disk = round(100*used/total,2)
    db = get_folder_size(current_app.config['DATABASE_FOLDER'])
    return jsonify(dict(disk=disk, diskusage=f"{round(used/2**30,2)}GB / {total//2**30}GB",
                        database=max(round(100*db/used, 2), 15), dbusage=f"{round(db/2**30,2)}GB"))


@bp.route('/get_access_log', methods=['POST'])
def get_access_log():
    hour = datetime.now().hour+1
    timepoints = [hour-i if (hour-i)>0 else (24 + hour-i) for i in range(23)]
    data = [] 
    for t in timepoints:
        al = AccessLog.query.get(t)
        count = al.count if al else 0
        data.append({'time':t,'value':count})
    return jsonify(data[::-1])
