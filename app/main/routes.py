from app import db
from flask import render_template, flash, redirect,url_for,request,current_app
from flask_login import current_user,login_required
from datetime import datetime
from app.main import bp
from app.models import Selection, Rounds, models_table_name_dictionary , SeqRound,Project,PPT
from flask import g
from app.main.forms import SearchNGSForm, SearchInventoryForm, TestForm, SearchPPTForm,UserSettingForm
from urllib.parse import urlparse
from app.utils.ngs_util import pagination_gaps,reverse_comp,validate_sequence
from sqlalchemy import or_
from app.ppt.routes import ppt_search_handler

@bp.before_app_request
def before_request():
    formdict = {'NGS': SearchNGSForm,
                'FOLD': SearchInventoryForm, 'INVENTORY': SearchInventoryForm,
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
          


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('index.html',title='Home')



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
    if method == 'text':
        entries, total = target.search(form.q.data,page,pagelimit)
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
        return render_template('search/search_result.html',content='Not implemented yet.')
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
