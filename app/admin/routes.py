from app import db
from flask import render_template, flash, redirect,url_for,request,current_app
from flask_login import current_user,login_required
from datetime import datetime
from app.admin import bp
from app.models import Selection, Rounds, models_table_name_dictionary , SeqRound
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
    try:
        for k,item in models_table_name_dictionary.items():
            if 'SearchableMixin' in [i.__name__ for i in item.__bases__]:
                item.reindex()
                flash('Reindex <{}>... success.'.format(k), 'success')
    except Exception as e:
        flash(str(e),'danger')
        return render_template('admin/result.html',content='Shit happened.')
    return render_template('admin/result.html', content='Success.')
