from app import db
from flask import render_template, flash, redirect, url_for, request, current_app, send_from_directory,jsonify
from flask_login import current_user,login_required
from datetime import datetime
from app.ppt import bp
from app.models import Selection, Rounds, models_table_name_dictionary , SeqRound,PPT,Slide,Project
from flask import g
from app.ppt.forms import SearchNGSForm, SearchInventoryForm, TestForm
from urllib.parse import urlparse
from app.utils.ngs_util import pagination_gaps
from sqlalchemy import or_

#TODO
#1. search
#2. display trashed slides with notes. 
#3. 
def remove_thurmbnail_from_url(url):
    return '&'.join(i for i in url.split('&') if 'thumbnail' not in i)


@bp.after_request
def add_header(response):
    response.cache_control.max_age = 60
    return response

@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    pagelimit = current_user.slide_per_page
    table = request.args.get('table',None)
    if not table:
        return redirect(url_for('ppt.index',table='ppt'))
    
    id = request.args.get('id', 0, type=int)
    page = request.args.get('page', 1, type=int)
    target = models_table_name_dictionary.get(table, None)
   
    tag = request.args.get('tag' , None)
    if table == 'tags' and tag==None:
        return render_template('ppt/index.html', title='Browse-' + (table.upper() or ' '),  
                               table=table,  entries=Slide.tags_list(500,True),)
    if table == 'trash' or table == 'tags':
        target = Slide
        
    tags_list = Slide.tags_list()
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
            if table == 'trash':
                entries = target.query.filter_by(ppt_id=None).order_by(
                    target.date.desc(), target.page.desc()).paginate(page, pagelimit, False)
            elif table =='tags':
                table = 'slide'
                entries = target.query.filter(target.tag.contains(tag)).order_by(
                    target.date.desc(), target.page.desc()).paginate(page, pagelimit, False)
            elif table == 'slide':
                entries = target.query.filter(target.ppt_id!=None).order_by(
                    target.date.desc(), target.page.desc()).paginate(page, pagelimit, False)
            else:
                entries = target.query.order_by(
                    target.date.desc()).paginate(page, pagelimit, False)
        nextcontent = {'ppt': 'slide',
                       'project': 'ppt'}.get(table)
        kwargs = {}
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
        return render_template('ppt/index.html', title='Browse-' + (table.upper() or ' '), entries=entries.items, 
                               next_url=next_url, prev_url=prev_url, table=table, nextcontent=nextcontent, tags_list=tags_list,
                               page_url=page_url, active=page,id=id)
        
    return render_template('ppt/index.html', title='Browse-' + (table.upper() or ' '), 
                           table=table,  tags_list=tags_list,)


@bp.route('/user_follow_slides', methods=['GET', 'POST'])
@login_required
def user_follow_slides():
    ppt_id = request.args.get('id',0)
    pagelimit = current_user.slide_per_page
    page = request.args.get('page', 1, type=int)
    if ppt_id:
        slides_id = current_user.follow_ppt_update().get(str(ppt_id),[])
        if not slides_id:
            return redirect(url_for('ppt.index',table='slide',id=ppt_id))
    else:
        slides_id = [i for k in current_user.follow_ppt_update().values() for i in k]
    entries = Slide.query.filter(Slide.id.in_(slides_id)).order_by(Slide.date.desc(),Slide.page.desc()).paginate(page, pagelimit, False)
    totalpages = entries.total
    start, end = pagination_gaps(page, totalpages, pagelimit, gap=15)

    next_url = url_for('ppt.slide_cart',
                       page=entries.next_num,) if entries.has_next else None
    prev_url = url_for('ppt.index',
                       page=entries.prev_num, ) if entries.has_prev else None
    page_url = [(i, url_for('ppt.slide_cart',  page=i, ))
                for i in range(start, end+1)]
    return render_template('ppt/slide_comparison.html', title='Project-Update', entries=entries.items,
                           next_url=next_url, prev_url=prev_url, tags_list=Slide.tags_list(),
                           page_url=page_url, active=page, backurl=request.referrer, mode="update", ppt_id=ppt_id)
   


@bp.route('/slide_cart', methods=['GET', 'POST'])
@login_required
def slide_cart():
    pagelimit = current_user.slide_per_page
    page = request.args.get('page', 1, type=int)
    when = [(j,i) for i,j in enumerate(current_user.slide_cart)]
    entries = Slide.query.filter(Slide.id.in_(current_user.slide_cart)).order_by(db.case(when,value=Slide.id)).paginate(page,pagelimit,False)
    totalpages = entries.total
    
    start, end = pagination_gaps(page, totalpages, pagelimit, gap=15)

    next_url = url_for('ppt.slide_cart', 
                       page=entries.next_num,) if entries.has_next else None
    prev_url = url_for('ppt.index', 
                       page=entries.prev_num, ) if entries.has_prev else None
    page_url = [(i, url_for('ppt.slide_cart',  page=i, ))
                for i in range(start, end+1)]
    
    return render_template('ppt/slide_comparison.html', title='Slides-Comparison', entries=entries.items, 
                           next_url=next_url, prev_url=prev_url, tags_list=Slide.tags_list(),
                           page_url=page_url, active=page, backurl=request.referrer,mode="selected")

@bp.route('/tags/<tag>', methods=['GET'])
@login_required
def tags(tag):
    return ppt_search_handler(str(tag),['tag'],['all'])


@bp.route('/add_flag', methods=['POST'])
@login_required
def add_flag():
    try:
        flag = request.json.get('flag')
        id=request.json.get('slide_id')
        slide = Slide.query.get(id)
        if flag!='none':
            slide._flag = flag
            db.session.commit()
            messages = [('success',"{} was flagged as {}.".format(slide,flag.upper()))]
        else:
            slide._flag = None
            db.session.commit()
            messages = [('success', "{} was unflagged.".format(slide))]
    except Exception as e:
        messages = [('danger', "Error occurred during flagging {}: {}.".format(slide,e))]
    return jsonify(html=render_template('flash_messages.html',messages=messages))


@bp.route('/remove_all_slide_cart', methods=['GET'])
@login_required
def remove_all_slide_cart():
    current_user.slide_cart=[]
    current_user.save_data()
    db.session.commit()
    return redirect(url_for('ppt.index'))


@bp.route('/read_allslides', methods=['GET'])
@login_required
def read_allslides():
    try:
        ppt_id = request.args.get('ppt_id',0,int)
        print(ppt_id)
        if ppt_id:
            ppt = PPT.query.get(ppt_id)
            slides = [i.id for i in ppt.slides]
            current_user.follow_ppt.update({ppt_id: slides})
        else:
            for k in list(current_user.follow_ppt.keys()):               
                ppt = PPT.query.get(k)
                if ppt:
                    slides = [i.id for i in ppt.slides]
                    current_user.follow_ppt.update({k: slides})
                else:
                    current_user.follow_ppt.pop(k,None)
        current_user.save_data()
        db.session.commit()
        flash('All updates are marked as read.', 'info')
    except Exception as e:
        flash('Error during updating {}: {}'.format(ppt_id,e),'warning')
    return redirect(url_for('main.index'))



@bp.route('/add_to_slide_cart', methods=['POST'])
@login_required
def add_to_slide_cart():
    try:
        id = int(request.json.get('slide_id'))
        action = request.json.get('action')
        slide = Slide.query.get(id)
        if action=='delete':
            if id in current_user.slide_cart:
                current_user.slide_cart.remove(id)
                current_user.save_data()
                db.session.commit()
                messages=[]
        else:
            if (id not in current_user.slide_cart) and slide:
                current_user.slide_cart.append(id)
                current_user.save_data()
                db.session.commit()
                messages = [('success', "{} was added to your comparison.".format(slide))]
            else:
                messages = [('info', "Side {} is already added or don't exist anymore.".format(id))]
    except Exception as e:
        messages = [
            ('danger', "Error occurred: {}.".format(e))]
    return jsonify(slide_count= len(current_user.slide_cart),html=render_template('flash_messages.html', messages=messages))


@bp.route('/add_ppt_to_follow', methods=['POST'])
@login_required
def add_ppt_to_follow():
    try:
        id = request.json.get('ppt_id')
        action  = request.json.get('action')
        ppt=PPT.query.get(id)
        if action == 'Follow':
            slides = [i.id for i in ppt.slides]
            current_user.follow_ppt.update({id:slides})
            messages = [
                ('success', "You are now following <{}>.".format(ppt.name))]
        else:
            current_user.follow_ppt.pop(id,None)
            messages = [
                ('success', "You unfollowed <{}>.".format(ppt.name))]
        current_user.save_data()
        db.session.commit()
    except Exception as e:
        messages = [
            ('danger', "Error occurred during {} PPT_id <{}>: {}.".format(action,id,e))]
    return jsonify(status=current_user.is_following_ppt(id), html=render_template('flash_messages.html', messages=messages))


def ppt_search_handler(query, field, ppt):
    """
    test, ['all'], ['all','tag'], ['all']
    string, ['9'], ['all', 'title', 'body'], ['15', '16']
    """
    thumbnailurl=remove_thurmbnail_from_url(request.url)
    page = request.args.get('page', 1, int)
    pagelimit = current_user.slide_per_page
    kwargs={}
    for k in request.args:
        kwargs[k] = (request.args.getlist(k))
    
    thumbnail = request.args.get('thumbnail', 'small')
    kwargs.pop('page', None)
    kwargs.update(thumbnail=thumbnail)
    entries,total = Slide.search_in_id(query,field,ppt,page,pagelimit)
    start, end = pagination_gaps(page, total, pagelimit)
    next_url = url_for('main.search', page=page+1, **
                       kwargs) if total > page*pagelimit else None
    prev_url = url_for('main.search', page=page-1, **
                       kwargs) if page > 1 else None
    page_url = [(i, url_for('main.search', page=i, **kwargs))
                for i in range(start, end+1)]

    tags_list = Slide.tags_list()

    return render_template('ppt/index.html', title='Slide Search result' , entries=entries, thumbnail=thumbnail,thumbnailurl=thumbnailurl,
                           next_url=next_url, prev_url=prev_url, table='slide', nextcontent=None, tags_list=tags_list,
                           page_url=page_url, active=page, id=id)

@bp.route('/get_ppt_slides', methods=['GET'])
def get_ppt_slides():
    filename = request.args.get('filename')
    return send_from_directory(current_app.config['PPT_TARGET_FOLDER'], filename, as_attachment=False)


@bp.route('/edit', methods=['POST'])
def edit():
    data = request.json
    table,field,id,value = data['table'],data['field'],data['id'],data['data']
    target = models_table_name_dictionary.get(table, None)
    try:
       
        item = target.query.get(id)
        setattr(item,field,value)
        db.session.commit()
        messages=[('success','Edit to {}\'s {} was saved.'.format(item,field))]
    except Exception as e:
        messages = [
            ('danger', 'Edit to {}\'s {} failed. Error: {}'.format(item, field ,e))]
    return jsonify(html=render_template('flash_messages.html',messages=messages),tag=getattr(item,'tag',None),note=item.note)


@bp.route('/get_ppt_by_project', methods=['POST'])
def get_ppt_by_project():
    project = request.json['project']
   
    if 'all' in project:
        result = db.session.query(PPT.id, PPT.name).order_by(
            PPT.date.desc()).all()
    else:
        project = [int(i) for i in project]
        result = db.session.query(PPT.id, PPT.name).filter(PPT.project_id.in_(project)).order_by(
            PPT.date.desc()).all()
    return jsonify({'options':result})
