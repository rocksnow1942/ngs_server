from app import db
from flask import render_template, flash, redirect,url_for,request,current_app
from flask_login import current_user,login_required
from datetime import datetime
from app.main import bp
from app.models import Selection,Rounds


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('index.html',title='Home')



@bp.route('/triggererror', methods=['GET', 'POST'])
def triggererror():
    assert False, ('new error')    
    return render_template('upload.html',title='Upload',form={'form':'upload'})



@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    print(request.form['search_para'])
    
    return render_template('search/search_result.html', title='Search Result', para=request.form['search_para'])
