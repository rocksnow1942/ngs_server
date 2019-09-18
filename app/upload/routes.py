from app import db
from flask import render_template, flash, redirect,url_for,request,current_app,abort
from flask_login import current_user,login_required
from datetime import datetime
from app.upload import bp
from app.models import Selection,Rounds,Primers,Sequence,SeqRound,NGSSampleGroup
from werkzeug.utils import secure_filename
from app.utils.ngs_util import check_file_reverse_comp,create_folder_if_not_exist
import os
import json

@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('upload/upload.html',title='Upload')

def allowed_file(*files,fileextension=[]):
    if isinstance(fileextension,str): fileextension = [fileextension]
    allowedextension = fileextension or current_app.config['ALLOWED_EXTENSIONS']
    for f in files:
        if ('.' in f.filename) and (f.filename.rsplit('.', 1)[1].lower()
                in allowedextension):
            continue
        else:
            return False
    return True

def process_ngssample_files(file1,file2):

    assert check_file_reverse_comp(file1,file2), ('Two many sequences are not reverse complementary.')
    savefolder = current_app.config['UPLOAD_FOLDER']
    create_folder_if_not_exist(savefolder)
    f1,f2 = secure_filename(file1.filename),secure_filename(file2.filename)
    f1 = f1.rsplit('.',1)[0]+datetime.now().strftime("%m%d%H%M%S")+'-1.'+f1.rsplit('.',1)[1]
    f2 = f2.rsplit('.',1)[0]+datetime.now().strftime("%m%d%H%M%S")+'-2.'+f2.rsplit('.',1)[1]
    file1.save(os.path.join(savefolder, f1))
    file2.save(os.path.join(savefolder, f2))
    return f1,f2

@bp.route('/ngsuploadwidget', methods=['POST'])
@login_required
def ngsuploadwidget():
    returnurl = request.referrer
    if request.method=='POST':
        if ('file1' not in request.files) or ('file2' not in request.files) :
            flash('Must upload both forward and reverse read at same time.','warning')
            return redirect(returnurl)
        file1,file2 = request.files['file1'],request.files['file2']
        if file1.filename == '' or file2.filename=='':
            flash('Need both files.','warning')
            return redirect(returnurl)
        if allowed_file(file1,file2,fileextension='fastq'):
            try:
                f1,f2=process_ngssample_files(file1,file2)
                id = request.args.get('uploadto',1,type=int)
                sg=NGSSampleGroup.query.get(id)
                tosavename = json.dumps({'file1': f1, 'file2': f2})
                assert len(tosavename)<=199, ('File names too long. Max length <80.')
                sg.datafile=tosavename
                sg.processingresult=''
                sg.task_id=None
                db.session.commit()
                flash('File <{},{}> Uploaded.'.format(f1,f2),'success')
            except Exception as e:
                flash('Exception: {}'.format(e),'danger')
        else:
            flash('File type not allowed.','warning')

        return redirect(request.referrer)
    return render_template('upload/uploadwidget.html',title='Upload')





@bp.route('/error', methods=['GET', 'POST'])
@login_required
def details():
    abort(404)
