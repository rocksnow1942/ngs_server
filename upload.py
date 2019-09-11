import os
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
import datetime
from flask_uploads import UploadSet,IMAGES,configure_uploads



UPLOAD_FOLDER = '/Users/hui/Documents/Scripts/flask/static/temp'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','csv','sql'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'secret'
app.config['UPLOADS_DEFAULT_DEST'] = UPLOAD_FOLDER
# app.config['UPLOADS_DEFAULT_URL'] = 



images = UploadSet('images',IMAGES)
configure_uploads(app,images)




def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = filename.rsplit('.',1)[0]+datetime.datetime.now().strftime("%m%d_%H%M%S")+'.'+filename.rsplit('.',1)[1]
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

#
#
# from werkzeug import SharedDataMiddleware
# app.add_url_rule('/uploads/<filename>', 'uploaded_file',
#                  build_only=True)
# app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
#     '/uploads':  app.config['UPLOAD_FOLDER']
# })
#
from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


#
#
# @app.route('/<filename>', methods=['GET', 'POST'])
# def uploaded_file(filename):
#     pathtofile=os.path.join(app.config['UPLOAD_FOLDER'], filename)
#     print(pathtofile)
#     return '''
#     <!doctype html>
#     <title>uploaded</title>
#     <h1>uploaded {}</h1>
#     <img src="static/temp/{}">
#
#     '''.format(filename,filename)
