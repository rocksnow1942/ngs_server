from app import db
from flask import render_template, flash, redirect,url_for,request,current_app
from flask_login import current_user,login_required
from datetime import datetime
from app.admin import bp
from app.models import Selection, Rounds, models_table_name_dictionary , SeqRound,Project,PPT,Slide
from flask import g
# from app.admin.forms import SearchNGSForm, SearchInventoryForm, TestForm
from urllib.parse import urlparse
from app.utils.ngs_util import pagination_gaps,reverse_comp,validate_sequence
from sqlalchemy import or_

@bp.route('/', methods=['GET', 'POST'])
@login_required
def admin():
    return render_template('admin/index.html',title='Admin Page')


@bp.route('/clear_trash', methods=['GET', 'POST'])
def clear_trash():
    # TODO
    # need to delete trash from SQL tasks, and unused analysis folders.
    # clear up file uploads.
    return None


@bp.route('/reindex_models', methods=['GET', 'POST'])
def reindex_models():
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
