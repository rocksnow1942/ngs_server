from app import db
from flask import render_template, flash, redirect,url_for,request,current_app,abort,jsonify
from flask_login import current_user,login_required
from datetime import datetime
from app.upload import bp
from app.models import Selection,Rounds,Primers,Sequence,SeqRound,NGSSampleGroup
from werkzeug.utils import secure_filename
from app.utils.ngs_util import check_file_reverse_comp,create_folder_if_not_exist
import os
import json

# @bp.route('/', methods=['GET', 'POST'])
# @login_required
# def index():
#     return render_template('upload/upload.html',title='Upload')

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
    # assert check_file_reverse_comp(file1,file2), ('Two many sequences are not reverse complementary.')
    savefolder = current_app.config['UPLOAD_FOLDER']
    create_folder_if_not_exist(savefolder)
    f1 = secure_filename(file1.filename)
    f1 = f1.rsplit('.',1)[0]+datetime.now().strftime("_%Y%m%d_%H%M%S")+'-1.'+f1.rsplit('.',1)[1]
    file1.save(os.path.join(savefolder, f1))

    f2 = secure_filename(file2.filename)
    if f2: 
        f2 = f2.rsplit('.',1)[0]+datetime.now().strftime("_%Y%m%d_%H%M%S")+'-2.'+f2.rsplit('.',1)[1]
        file2.save(os.path.join(savefolder, f2))
    return f1,f2

@bp.route('/ngsuploadwidget', methods=['POST'])
@login_required
def ngsuploadwidget():
    returnurl = request.referrer
    id = request.args.get('uploadto', 1, type=int)
    sg = NGSSampleGroup.query.get(id)
    if request.method=='POST':
        if ('file1' not in request.files) : #or ('file2' not in request.files) :
            flash('Must upload files.','warning') #both forward and reverse read at same time.
            return redirect(returnurl)
        file1,file2 = request.files['file1'],request.files.get('file2',None)
        if file1.filename == '' and file2.filename=='':
            # if file already exist, don't overwrite. 
            sgfiles = sg.files
            if sgfiles and (os.path.exists(sgfiles[0]) or os.path.exists(sgfiles[1])):
                flash('Data files already uploaded. Cannot overwrite it with empty files.')

            else:
                flash('No files uploaded. Filenames auto generated, place Fastq files in upload folder before proceed.','warning')
                f1 = sg.name + '_R1.fastq'
                f2 = sg.name + '_R2.fastq'
                tosavename = json.dumps({'file1': f1, 'file2': f2})
                sg.datafile = tosavename
                sg.processingresult = ''
                sg.task_id = None
                db.session.commit()
            return redirect(returnurl)
        if allowed_file(file1, fileextension=['fastq','gz']):
            try:
                f1,f2=process_ngssample_files(file1,file2)
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


@bp.route('/ngscopydatafile', methods=['POST'])
@login_required
def ngscopydatafile():
    uploadto = request.json.get('uploadto',None)
    target = request.json.get('target',None)
    SG = NGSSampleGroup.query.get(uploadto)
    targetSG = NGSSampleGroup.query.get(target)
    refresh = False
    if not SG:
        msg = [('warning',f"NGS sample group ID <{uploadto}> doesn't exist")]
        return jsonify(html=render_template('flash_messages.html', messages=msg))
    if not targetSG:
        msg = [('warning', f"NGS sample group ID <{target}> doesn't exist!")]
        return jsonify(html=render_template('flash_messages.html', messages=msg))

    sgfiles = targetSG.files
    if sgfiles and (os.path.exists(sgfiles[0]) or os.path.exists(sgfiles[1])):
        SG.datafile = targetSG.datafile
        db.session.commit()
        msg = [('success',f"Copied datafile from ID<{target}> to ID<{uploadto}>")]
        refresh = True
    else:
        msg = [('warning',f"Data files of <{target}> are not valid.")]
   
    return jsonify(html=render_template('flash_messages.html', messages=msg),refresh=refresh)
