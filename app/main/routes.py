from app import db
from flask import render_template, flash, redirect, url_for, request, current_app, jsonify, abort
from flask_login import current_user,login_required
from datetime import datetime
from app.main import bp
from app.models import AccessLog,Selection, Rounds, models_table_name_dictionary , SeqRound,Project,PPT,Sequence,Task
from flask import g
from app.main.forms import SearchNGSForm, SearchPPTForm,UserSettingForm
from urllib.parse import urlparse
from app.utils.ngs_util import pagination_gaps,reverse_comp,validate_sequence
from sqlalchemy import or_,func
from app.ppt.routes import ppt_search_handler
# from app.utils.analysis._alignment import lev_distance
from app.utils.common_utils import get_part_of_day, parse_url_path
from app.utils.ngs_util import convert_string_to_id
from dateutil import parser
from inspect import signature

def white_ip_list(ip):
    """
    only allow access from certain ip address. 
    """
    first3 = ip.rsplit(".", 1)[0]
    if  first3 in ("192.168.86","127.0.0"):
        return True  
    elif ip == "68.6.106.82":
        return True

@bp.before_app_request
def before_request():
    ipaddr = request.remote_addr
    if not white_ip_list(ipaddr):
        abort(404)
    # abort(404)
    formdict = {'NGS': SearchNGSForm,
                'PPT':SearchPPTForm}
    root = urlparse(request.url).path.split('/')[1]
    formtype = root.upper() if root != 'search' else request.args.get(
        'submit', 'submit PPT').split()[-1]
    # print(request.form)
    g.search_form = formdict.get(formtype.upper(), SearchNGSForm)()   
    if formtype == 'PPT': # dynamically add Search PPT form optioins and data
        g.search_form.search_project.choices = [
            ('all', 'All'), ] + [(p.id, p.name) for p in Project.query.all()]
        g.search_form.search_project.data = g.search_form.search_project.data or ['all']
        g.search_form.search_field.data = g.search_form.search_field.data or ['all']
        g.search_form.search_ppt.data = g.search_form.search_ppt.data or ['all']
        project = g.search_form.search_project.data
        if 'all' in project:
            result = db.session.query(PPT.id, PPT.name).order_by(
            PPT.date.desc()).all()
        else:
            project = [int(i) for i in project]
            result = db.session.query(PPT.id, PPT.name).filter(PPT.project_id.in_(project)).order_by(
                PPT.date.desc()).all()
        g.search_form.search_ppt.choices = [('all', 'All'),]+ result

    if request.method=='GET': 
        hour = datetime.now().hour+1
        al=AccessLog.query.get(hour)
        if al:
            al.add_count()
        else:
            db.session.add(AccessLog(id=hour, count=1))
        db.session.commit()

def privilege_required(privilege='user'):
    allowed_roles = {"user":["user",'manager','admin'],"manager":['admin','manager'],'admin':["admin"]}[privilege]
    def decorator(func):
        sig = signature(func)
        def wrapper(*args,**kwargs):
            if current_user.privilege in allowed_roles:
                return func(*args,**kwargs)
            else:
                return render_template('main/privilege.html')
        wrapper.__signature__ = sig
        wrapper.__name__=func.__name__
        return wrapper
    return decorator


@bp.route('/pptmonitor_port', methods=['POST'])
def pptmonitor_port():
    result = request.json 
    time = parser.parse(result['time'])
    msg = result['msg']
    if msg == 'monitor':
        task = Task.query.get('pptmonitor_status_entry')
        if not task:
            return 'restart'
        dt = (datetime.now() - task.date)
        dt = dt.seconds//60
        if dt > 30: # if over 30minutes not hearing back, restart. 
            return 'restart'
    else:
        task = Task.query.get('pptmonitor_status_entry') or Task(id='pptmonitor_status_entry')
        task.date = time
        task.name = msg
        db.session.add(task)
        db.session.commit()
    # return render_template('main/index.html', title='Home', follow_ppt=entries, greet=greet, linkentries=linkentries)
    return 'ok'

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    follow_ppt = current_user.follow_ppt.keys()
    entries = PPT.query.filter(PPT.id.in_(follow_ppt)).all()
    greet = get_part_of_day(datetime.now().hour)
    linkentries = current_user.quick_link 
    ppttask = Task.query.get('pptmonitor_status_entry') 
    if ppttask:
        dt = (datetime.now() - ppttask.date)
        pptindextime = dt.seconds//60 
    else:
        pptindextime = 60
    return render_template('main/index.html', title='Home', follow_ppt=entries, greet=greet, pptindextime=pptindextime, linkentries=linkentries)


@bp.route('/edit_link', methods=['GET', 'POST'])
@login_required
def edit_link():
    form = request.form
    delete = request.args.get('delete', None)
    if form and request.method=='POST':
        idx = int(form.get('id'))
        name = form.get('name')
        url = parse_url_path(form.get('url'))
        if idx == -1:
            current_user.quick_link.append((name, url))
        else:
            current_user.quick_link[idx] = (name, url)
        current_user.save_data()
        db.session.commit()
    if delete != None:
        current_user.quick_link.pop(int(delete))
        current_user.save_data()
        db.session.commit()
    return redirect(url_for('main.index'))





@bp.route('/triggererror', methods=['GET', 'POST'])
def triggererror():
    assert False, ('new error')
    return None


@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form=g.search_form
    formtype = form.__class__.__name__#request.args.get('submit', None).split()[-1]
  
    if formtype == 'SearchNGSForm':
        return ngs_serach_handler(form)
    elif formtype == 'SearchPPTForm':
        query,project,field,ppt = form.q.data,form.search_project.data,form.search_field.data,form.search_ppt.data
        if 'all' in ppt:      
            ppt = [i[0] for i in form.search_ppt.choices if i[0]!='all']
        return ppt_search_handler(query, field, ppt)
    return render_template('search/search_result.html', title='Search Result', content='def', )

        
def ngs_serach_handler(form):
    pagelimit = current_user.ngs_per_page
    table=form.search_field.data
    target = models_table_name_dictionary.get(table)
    method = form.search_method.data
    page = request.args.get('page',1,int)
    kwargs = dict(request.args)
    kwargs.pop('page', None)
    nextcontent = {'round': 'sequence_round', 'selection': 'round'}.get(table)
    seqdict = dict(primer='sequence', known_sequence='rep_seq',
                   sequence='aptamer_seq')
    if method == 'text':
        if table=='sequence':
            table = 'sequence_round'
            sequences = db.session.query(Sequence.id).filter(Sequence.note.contains(form.q.data)).subquery()
            maxcounts = db.session.query(SeqRound.sequence_id,func.max(SeqRound.count).label('count')).filter(SeqRound.sequence_id.in_(sequences)).group_by(SeqRound.sequence_id).subquery()
            result = SeqRound.query.join(Sequence,SeqRound.sequence_id==Sequence.id).filter(SeqRound.sequence_id==maxcounts.c.sequence_id,SeqRound.count==maxcounts.c.count).order_by(Sequence.date.desc())
            result = result.paginate(page, pagelimit, False)
            total = result.total
            entries = result.items
          
            # subqry = db.session.query(func.max(sr.count)).filter(sr.sequence_id.in_([1,2,3,4,5])) 
            # sr.query.filter(sr.sequence.in_([1,2,3,4,5],sr.count==subqry)).all()

            # subq=db.session.query(sr.sequence_id,func.max(sr.count).label('count')).filter(sr.sequence_id.in_([1,2,3,4,5])).group_by(sr.sequence_id).subquery()
            # sr.query.filter(sr.sequence_id==subq.c.sequence_id,sr.count==subq.c.count).all()

        else:
            entries, total = target.search(form.q.data,page,pagelimit)
    elif method == 'name':
        q = form.q.data 
        if table=='sequence':
            table = 'sequence_round'
            try:
                seqid=convert_string_to_id(q)
            except:
                seqid=0
            result = SeqRound.query.filter(SeqRound.sequence_id==seqid).order_by(SeqRound.count.desc())
        else:
            namedict = dict(analysis="name", known_sequence='sequence_name', selection='selection_name', round='round_name',primer='name', ngs_sample_group='name')
            result = target.query.filter(getattr(target,namedict[table]).contains(q)).order_by(target.id.desc())
        result = result.paginate(page, pagelimit, False)
        total = result.total
        entries = result.items
    elif method == 'sequence':
        seq = form.q.data
        if not validate_sequence(seq): 
            flash('Sequence not valid. Only ATCG is allowed.','warning')
            return redirect(request.referrer)
        revseq = reverse_comp(seq)
        seqdict = dict(primer='sequence',known_sequence='rep_seq',sequence='aptamer_seq')
        stmt = or_(getattr(target,seqdict[table]).contains(seq), getattr(target,seqdict[table]).contains(revseq))
        
        if table=='sequence':
            table='sequence_round'
            result = SeqRound.query.filter(SeqRound.sequence_id.in_(
                db.session.query(target.id).filter(stmt))).order_by(SeqRound.count.desc())
        else:
            result = target.query.filter(stmt).order_by(target.id.desc())
        result = result.paginate(page, pagelimit, False)
        total=result.total
        entries=result.items

    elif method == 'distance':
        seq = form.q.data
        if not validate_sequence(seq):
            flash('Sequence not valid. Only ATCG is allowed.', 'warning')
            return redirect(request.referrer)
        taskid = current_user.launch_search(seq,table)
        target = models_table_name_dictionary.get(table)
        total = target.query.count()
        # render a template to display progress bar with task id, after done display result page. 
        return render_template('ngs/task_progress.html',task_id=taskid,table=table,total=total)
    start, end = pagination_gaps(page, total, pagelimit)
    next_url = url_for('main.search', page=page+1, **
                       kwargs) if total > page*pagelimit else None
    prev_url = url_for('main.search', page=page-1, **
                       kwargs) if page > 1 else None
    page_url = [(i, url_for('main.search', page=i, **kwargs))
                for i in range(start, end+1)]
    return render_template('ngs/browse.html', title='Search Result', table=table,
                           nextcontent=nextcontent, entries=entries, next_url=next_url, prev_url=prev_url, page_url=page_url, active=page)


@bp.route('/analysis_log', methods=['GET', 'POST'])
def analysis_profile():
    return render_template('ngs/analysis_profile.html', user=current_user, title='NGS analysis')


@bp.route('/user_settings', methods=['GET', 'POST'])
def user_settings():
    form = UserSettingForm(obj=current_user)
    if form.validate_on_submit():
        user = form.populate_obj(current_user)
        db.session.commit()
        flash('Settings Saved','success')
        return redirect(request.referrer)
    return render_template('auth/profile.html', user=current_user, title='Settings', form=form)


@bp.route('/user_settings_ajax', methods=['POST'])
def user_settings_ajax():
    data = request.json.get('setting')
    current_user.user_setting.update(data)
    current_user.save_data()
    db.session.commit()
    messages = [('success',"Setting <{}> set to <{}>.".format(k,i)) for k,i in data.items()]
    return jsonify(html=render_template('flash_messages.html', messages=messages))
