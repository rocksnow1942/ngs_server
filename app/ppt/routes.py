from app import db
from flask import render_template, flash, redirect, url_for, request, current_app, send_from_directory,jsonify
from flask_login import current_user,login_required
from datetime import datetime
from app.ppt import bp
from app.models import Selection, Rounds, models_table_name_dictionary , SeqRound
from flask import g
from app.ppt.forms import SearchNGSForm, SearchInventoryForm, TestForm
from urllib.parse import urlparse
from app.utils.ngs_util import pagination_gaps
from sqlalchemy import or_

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    pagelimit = 40
    table = request.args.get('table','ppt')
    id = request.args.get('id', 0, type=int)
    page = request.args.get('page', 1, type=int)
    target = models_table_name_dictionary.get(table, None)
    thumbnail = request.args.get('thumbnail','small')
    tags_list = []
    if table=='slide':
        tags_list = list(target.tags_list())
        
    if target:
        if id:
            if table == 'ppt':
                entries = target.query.filter_by(project_id=id).order_by(
                    target.date.desc()).paginate(page, pagelimit, False)
            elif table == 'slide':
                entries = target.query.filter_by(ppt_id=id).order_by(
                    target.date.desc(), target.page.desc()).paginate(page, pagelimit, False)
            else:
                entries = target.query.order_by(
                    target.date.desc()).paginate(page, pagelimit, False)
        else:
            entries = target.query.order_by(
                target.date.desc()).paginate(page, pagelimit, False)

        nextcontent = {'ppt': 'slide',
                       'project': 'ppt'}.get(table)
        kwargs = {'thumbnail':thumbnail}
        if id:
            kwargs.update(id=id)
        totalpages = entries.total
        start, end = pagination_gaps(page, totalpages, pagelimit,gap=15)

        next_url = url_for('ppt.index', table=table,
                           page=entries.next_num, **kwargs) if entries.has_next else None
        prev_url = url_for('ppt.index', table=table,
                           page=entries.prev_num, **kwargs) if entries.has_prev else None
        page_url = [(i, url_for('ppt.index', table=table, page=i, **kwargs))
                    for i in range(start, end+1)]
        return render_template('ppt/index.html', title='Browse-' + (table.upper() or ' '), entries=entries.items,thumbnail=thumbnail,
                               next_url=next_url, prev_url=prev_url, table=table, nextcontent=nextcontent, tags_list=tags_list,
                               page_url=page_url, active=page)
    return render_template('ppt/index.html', title='Browse-' + (table.upper() or ' '),  thumbnail=thumbnail,
                           table=table,  tags_list=tags_list,
                          )



@bp.route('/get_ppt_slides/<path:filename>', methods=['GET'])
def get_ppt_slides(filename):
    return send_from_directory(current_app.config['PPT_TARGET_FOLDER'], filename, as_attachment=True)


@bp.route('/edit', methods=['POST'])
def edit():
    data = request.json
    table,field,id,value = data['table'],data['field'],data['id'],data['data']
    target = models_table_name_dictionary.get(table, None)
    try:
        print(table, field, id, value)
        item = target.query.get(id)
        setattr(item,field,value)
        db.session.commit()
        messages=[('success','Edit to {}\'s {} was saved.'.format(item,field))]
    except Exception as e:
        messages = [
            ('danger', 'Edit to {}\'s {} failed. Error: {}'.format(item, field ,e))]

    return jsonify(html=render_template('flash_messages.html', messages=messages),tag=getattr(item,'tag',None),note=item.note)
