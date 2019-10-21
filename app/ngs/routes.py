import io
from app import db
from matplotlib.backends.backend_svg import FigureCanvasSVG
from flask import render_template, flash, redirect, url_for, request, current_app, abort, jsonify, Response, send_from_directory
from flask_login import current_user,login_required
from datetime import datetime
from app.ngs import bp
from app.models import Analysis,Selection,Rounds,Primers,Sequence,SeqRound,NGSSampleGroup,NGSSample,KnownSequence
from app.ngs.forms import ngs_add_form_dictionary,ngs_edit_form_dictionary
from sqlalchemy.exc import IntegrityError
from app.models import models_table_name_dictionary
from app.utils.ngs_util import pagination_gaps


@bp.route('/', methods=['GET', 'POST'])
@login_required
def ngs():
    return render_template('ngs/ngs.html',title='NGS')


@bp.route('/browse', methods=['GET', 'POST'])
@login_required
def browse():
    pagelimit = current_user.ngs_per_page
    table = request.args.get('table')
    id = request.args.get('id',0,type=int)
    page = request.args.get('page',1,type=int)
    target = models_table_name_dictionary.get(table,None)
    if target:
        if id:
            if table=='round':
                entries = target.query.filter_by(selection_id=id).order_by(target.id.desc()).paginate(page,pagelimit,False)               
            elif table=='sequence_round':
                entries = target.query.filter_by(rounds_id=id).order_by(target.count.desc()).paginate(page,pagelimit,False)
                # entries = [SequenceDisplay(i.sequence,i.count,i.count/rd.totalread,rd.round_name) for i in r]
            else:
                entries = target.query.order_by(
                    target.id.desc()).paginate(page, pagelimit, False)
        else:
            entries = target.query.order_by(target.id.desc()).paginate(page,pagelimit,False)
          
        nextcontent = {'round':'sequence_round','selection':'round'}.get(table)
        kwargs={}
        if id: kwargs.update(id=id)
        totalpages = entries.total
        start,end = pagination_gaps(page,totalpages,pagelimit)
       
        next_url = url_for('ngs.browse',table=table,
                        page=entries.next_num,**kwargs) if entries.has_next else None
        prev_url = url_for('ngs.browse', table=table,
                        page=entries.prev_num,**kwargs) if entries.has_prev else None
        page_url = [ (i, url_for('ngs.browse',table=table,page=i,**kwargs)) for i in range(start,end+1)]
        return render_template('ngs/browse.html', title='Browse' + (table or ' '), entries=entries.items,
                            next_url=next_url, prev_url=prev_url, table = table,nextcontent=nextcontent,page_url=page_url,active=page)
    return render_template('ngs/browse.html', title='Browse', entries=[],table='')


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """
    to do: add dynamic roundname and target option for adding rounds, based on selected selection.
    """
    toadd = request.args.get('toadd')
    if toadd == 'ngs_sample_group':
        return redirect(url_for('ngs.addsample'))
    datalist = {}
    datalist = load_datalist(toadd)
    formtemplate = ngs_add_form_dictionary.get(toadd,None)
    if formtemplate is None: abort(404)
    form = formtemplate()
    if form.validate_on_submit():
        newitem = form.populate_obj()
        db.session.add(newitem)
        db.session.commit()
        flash('New {} added.'.format(toadd), 'success')
        # return redirect(url_for('ngs.add', toadd=toadd))
    return render_template('ngs/add.html', title='Add', table=toadd,form=form,datalist=datalist)

def load_datalist(toadd):
    if toadd=='round':
        return dict(selections=db.session.query(
            Selection.selection_name).all(),
            primers=db.session.query(Primers.name).filter(
                Primers.role.in_(('SELEX', 'PD'))).all(),
            rounds=db.session.query(Rounds.round_name).all(),
            targets=db.session.query(Selection.target).distinct().all())
    elif toadd=='selection':
        return dict(targets=db.session.query(Selection.target).distinct().all())
    elif toadd=='sequence_round':
        return dict(known_sequence=db.session.query(KnownSequence.sequence_name).all())
    else:
        return {}


@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    if request.method == 'GET':
        edit_redirect_url = request.referrer or '/'
    else:
        edit_redirect_url = request.form.get('edit_redirect_url','/')
    toadd = request.args.get('toadd')
    id = request.args.get('id')
    if toadd == 'analysis':
        return redirect(url_for('ngs.analysis', id=id))
    try:
        if toadd == 'sequence_round':
            id = id[1:-1].split(',')
            id = tuple(int(i) for i in id)
        else:
            id = int(id)
    except:
        abort(404)
    datalist = {}
    datalist = load_datalist(toadd)
    if toadd == 'ngs_sample_group':
        return redirect(url_for('ngs.addsample', id=id, edit_redirect_url=edit_redirect_url))
    elif toadd in ngs_edit_form_dictionary.keys():
        target = models_table_name_dictionary.get(toadd,None)
        formtemplate = ngs_edit_form_dictionary.get(toadd,None)
        if target and formtemplate:
            newitem = target.query.get(id)
            form = formtemplate(newitem)
    else:
        return redirect(edit_redirect_url)
    if request.method == 'GET':
            form.load_obj(id)
    if form.validate_on_submit():
        form.populate_obj(id)
        db.session.commit()
        flash('Your Edit to <{}> was saved.'.format(newitem),'success')
        return redirect(edit_redirect_url)
    
    return render_template('ngs/add.html', title='Edit', table=toadd, form=form, datalist=datalist, edit_redirect_url=edit_redirect_url)


@bp.route('/delete', methods=['POST','GET'])
@login_required
def delete():
    edit_redirect_url = request.referrer or '/'
    table = request.args.get('table')
    id = request.args.get('todelete',0,int)
    if table !='sequence_round':
        target = models_table_name_dictionary.get(table)
        todelete = target.query.get(id)
        if todelete.haschildren():
            flash('Cannot delete {}'.format(todelete),'warning')
        else:
            try:
                db.session.delete(todelete)
                db.session.commit()
                flash('{} was deleted.'.format(todelete), 'success')
            except IntegrityError as e:
                db.session.rollback()
                flash('Cannot delete {}. Exception: {}.'.format(todelete,e), 'danger')
    return redirect(edit_redirect_url)


@bp.route('/addsample', methods=['GET', 'POST'])
@login_required
def addsample():
    form = ngs_add_form_dictionary['ngs_sample_group']()
    id = request.args.get('id', 0, type=int)
    if request.method=='GET':
        edit_redirect_url = request.args.get('edit_redirect_url','/')
    else:
        edit_redirect_url = request.form.get('edit_redirect_url', '/')
       

    datalist={}
    datalist.update(selections=db.session.query(Selection.selection_name).all(),)
    plist = [(i.id,i.name) for i in Primers.query.filter_by(role='NGS').all()]
    rdlist = [(i.id,i.round_name) for i in Rounds.query.all()]
    title = 'Edit' if id else 'Add'
    if id:
        if request.method == 'GET':
            form.load_obj(id)
            form.ignore_duplicate.data=True
        elif request.method == 'POST':
            form.old_name = NGSSampleGroup.query.get(id).name
    for f in form.samples:
        f.form.fp_id.choices= plist
        f.form.rp_id.choices= plist
        f.form.round_id.choices = rdlist
    # if request.method == 'POST':
        # check if all fp an rp index are unique.
    # print(request.method, "***=>>", form.validate_on_submit())
    if form.validate_on_submit():   
        indextuple = []
        for i in form.samples:
            indextuple.append((i.form.fp_id.data,i.form.rp_id.data))
        if len(set(indextuple)) != len(indextuple):
            flash('Error: FP RP Index have duplicates. Check Primers.','warning')
            return render_template('ngs/editsample.html', title=title, form=form, toadd='NGS Sample', datalist=datalist, id=id, edit_redirect_url=edit_redirect_url)
        # if form.validate_name():
        #     flash('Name < {} > already used.'.format(form.name.data), 'danger')
        #     return render_template('ngs/editsample.html', title=title, form=form, toadd='NGS Sample', datalist=datalist, id=id, edit_redirect_url=edit_redirect_url)
        sequenced_round = form.validate_round()
        if sequenced_round:
            flash('Round {} already sequenced.'.format(', '.join(['<'+i+'>' for i in sequenced_round])),'warning')
            return render_template('ngs/editsample.html', title=title, form=form, toadd='NGS Sample', datalist=datalist, id=id, edit_redirect_url=edit_redirect_url)
        
        sg = form.populate_obj(NGSSampleGroup,id=id)
        for i in form.samples:
            sg.samples.append(i.form.populate_obj(NGSSample))
        db.session.add(sg)
        db.session.commit()
        msg = 'edited' if id else 'added'
        flash('<{}> was {}.'.format(sg,msg),'info')
        if id:
            return redirect(edit_redirect_url)
        else:
            return redirect(url_for('ngs.addsample'))
    return render_template('ngs/editsample.html', title=title, form=form, toadd='NGS Sample', datalist=datalist, id=id, edit_redirect_url=edit_redirect_url)


@bp.route('/add_extrasample', methods=[ 'POST'])
@login_required
def add_extrasample():
    form = ngs_add_form_dictionary['ngs_sample_group']()
    form.samples.append_entry()
    rdlist = [(i.id,i.round_name) for i in Rounds.query.all()]
    plist = [((i.id),i.name) for i in Primers.query.filter_by(role='NGS').all()]
    for f in form.samples:
        f.form.fp_id.choices= plist
        f.form.rp_id.choices= plist
        f.form.round_id.choices = rdlist
    return render_template('ngs/samples.html',form=form)


@bp.route('/delete_sample', methods=[ 'POST'])
@login_required
def delete_sample():
    todelete = request.args.get('todelete',type=int)
    form = ngs_add_form_dictionary['ngs_sample_group']()
    form.samples.entries.pop(todelete-1)
    rdlist = [(i.id,i.round_name) for i in Rounds.query.all()]
    plist = [((i.id),i.name) for i in Primers.query.filter_by(role='NGS').all()]
    for f in form.samples:
        f.form.round_id.choices = rdlist
        f.form.fp_id.choices= plist
        f.form.rp_id.choices= plist
    return render_template('ngs/samples.html',form=form)


@bp.route('/get_selection_round', methods=[ 'POST'])
@login_required
def get_selection_round():
    selection=request.form.get('selection')
    s = Selection.query.filter_by(selection_name=selection).first()
    if s:
        rounds=Rounds.query.filter_by(selection_id=s.id).order_by(Rounds.id.desc()).all()
        roundarray = [{'id':r.id,'name':r.round_name} for r in rounds]
        return jsonify({'rounds':roundarray})
    else:
        return jsonify({'rounds':[]})


@bp.route('/get_known_as_sequence', methods=['POST'])
@login_required
def get_known_as_sequence():
    ks = request.form.get('knownas')
    ks = KnownSequence.query.filter_by(sequence_name=ks).first()
    if ks:
        return jsonify({'sequence':ks.rep_seq})
    else:
        return jsonify({'sequence':'Not Defined.'})



@bp.route('/ngs_data_processing', methods=['GET', 'POST'])
@login_required
def ngs_data_processing():
    id = request.args.get('id',0,type=int)
    sg = NGSSampleGroup.query.get(id)
    if sg and sg.can_start_task():
        try:
            sg.files_validation()
            sg.launch_task()
        except Exception as e:
            flash(f"Validation Failed. ID:<{id}>, resaon:<{e}>.",'danger')
    else:
        flash(f'Cannot Process Data of Sample ID: <{id}>.','danger')
    return redirect(request.referrer)



@bp.route('/details', methods=['GET'])
@login_required
def details():
    pagelimit = current_user.ngs_per_page
    page = request.args.get('page', 1, type=int)
    table = request.args.get('table','',str)
    id = request.args.get('id')
    target = models_table_name_dictionary.get(table,None)
    if table=='analysis':
        return redirect(url_for('ngs.analysis',id=id))
    if not target: abort(404)
    try:
        if table =='sequence_round':
            id = id[1:-1].split(',')
            id = tuple(int(i) for i in id)
        else:
            id = int(id)
    except:
        abort(404)
    
    entry = target.query.get(id)
    if not entry: abort(404)
   
    if table=='selection':
        query_result = Rounds.query.filter_by(selection_id=id).order_by(Rounds.id.desc()).paginate(page,pagelimit,False)
        
    elif table=='round':
        query_result = SeqRound.query.filter_by(rounds_id=id).order_by(SeqRound.count.desc()).paginate(page,pagelimit,False)
        
    if table in ['selection','round']:
        next_url = url_for('ngs.details', table=table, id=id,
                           page=query_result.next_num, ) if query_result.has_next else None
        prev_url = url_for('ngs.details', table=table, id=id,
                           page=query_result.prev_num, ) if query_result.has_prev else None
        totalpages = query_result.total
        start, end = pagination_gaps(page, totalpages, pagelimit)
        page_url = [(i, url_for('ngs.details', table=table, page=i, id=id))
                    for i in range(start, end+1)]
        return render_template('ngs/details.html', title='Details', entry=entry, table=table,
                               query_result=query_result, next_url=next_url, prev_url=prev_url, active=page, page_url=page_url)


    return render_template('ngs/details.html', title = 'Details', entry = entry, table=table)
                          


@bp.route('/details/image/<funcname>',methods=['GET'])
@login_required
def details_image(funcname):
    id = request.args.get('id', 0, int)
    target = models_table_name_dictionary.get(funcname, None)
    entry = target.query.get(id)
    if funcname == 'round':
        fig = entry.plot_pie()
    if funcname == 'sequence':
        fig = entry.plot_structure()
    if funcname == 'known_sequence':
        fig = entry.plot_structure()
    buf = io.BytesIO()
    fig.savefig(buf, format="svg")
    plt_byte = buf.getvalue()
    buf.close()
    return Response(plt_byte, mimetype="image/svg+xml")


@bp.route('/add_to_analysis', methods=['POST'])
@login_required
def add_to_analysis():
    table,id = request.json['data']
    id = int(id)
    try:
        if table == 'delete':
            if (id in current_user.analysis_cart):
                current_user.analysis_cart.remove(id)
        else:
            if table == 'selection':
                sele = Selection.query.get(id)
                ids = [i.id for i in sele.rounds]
            elif table == 'round':
                ids = [id]
            ids = [i for i in ids if i not in current_user.analysis_cart]
            current_user.analysis_cart.extend(ids)
        current_user.save_data()
        db.session.commit()
    except:
        flash('An Error occured during editing analysis cart. Please refresh page.','warning')
    return jsonify({'analysis_count':current_user.analysis_cart_count(),'remaining':current_user.analysis_cart})



@bp.route('/analysis_cart', methods=['POST','GET'])
@login_required
def analysis_cart():
    cart = current_user.analysis_cart
    entries = [Rounds.query.get(i) for i in cart]
    return render_template('ngs/analysis_cart.html',entries=entries)


@bp.route('/add_analysis', methods=['POST'])
@login_required
def add_analysis():
    if request.method=='POST':
        cart = current_user.analysis_cart
        name = request.form['name']
        note = request.form['note']
        analysis = Analysis(name=name,note=note,)
        analysis._rounds=cart
        analysis.user=current_user
        analysis.save_data()
        db.session.add(analysis)
        current_user.analysis_cart=[]
        current_user.save_data()
        db.session.commit()
        flash(f'Analysis <{analysis}> added.','success')
    return redirect(url_for('ngs.analysis',id=analysis.id))

@bp.route('/analysis', methods=['POST','GET'])
@login_required
def analysis():
    id = request.args.get('id',0,int)
    analysis = Analysis.query.get(id)
    # datareader=analysis.get_datareader()
    if analysis.clustered:
        active_tab= 'result'
    elif analysis.analysis_file:
        active_tab='cluster'
    else:
        active_tab = 'load'
    return render_template('ngs/analysis.html', analysis=analysis,active_tab=active_tab)


@bp.route('/analysis/cluster', methods=['POST', 'GET'])
@login_required
def analysis_cluster():
    id = request.args.get('id', 0, int)
    analysis = Analysis.query.get(id)
    cluster = request.args.get('cluster', 'C1')
    info,clusters=analysis.cluster_display(cluster)
    colordict=dict(zip('ATCG-',['red','green','blue','orange','black']))
    return render_template('ngs/analysis_cluster.html',cluster=cluster,colordict=colordict, analysis=analysis,clusters=clusters,clusterinfo=info)


@bp.route('/analysis_image/<funcname>', methods=['GET'])
@login_required
def analysis_image(funcname):
    id = request.args.get('id', 0, int)
    cluster = request.args.get('cluster','C1')
    analysis = Analysis.query.get(id)
    if funcname == 'heatmap':
        fig = analysis.plot_heatmap()
    elif funcname == 'plot_logo':
        fig = analysis.plot_logo(cluster)
    buf = io.BytesIO()
    fig.savefig(buf, format="svg")
    plt_byte = buf.getvalue()
    buf.close()
    return Response(plt_byte, mimetype="image/svg+xml")

@bp.route('/load_analysis_rounds', methods=['POST'])
@login_required
def load_analysis_rounds():
    id = request.json['id']
    analysis = Analysis.query.get(id)
    task = analysis.load_rounds()
    return jsonify({"id":task.id})


@bp.route('/build_cluster', methods=['POST'])
@login_required
def build_cluster():
    id = request.json['id']
    analysis = Analysis.query.get(id)
    distance = request.json['distance']
    cutoff_l = request.json['cutoff_l']
    cutoff_u = request.json['cutoff_u']
    threshold =request.json['threshold']
    try:
        distance=int(distance)
        lb=int(cutoff_l)
        ub = int(cutoff_u)
        threshold=int(threshold)
        analysis.cluster_para = [distance,lb,ub,threshold]
        analysis.save_data()
        db.session.commit()
        task = analysis.build_cluster()
        return jsonify({"id": task.id})
    except Exception as e:
        return jsonify({"id":'','error':f"{e}"})


@bp.route('/eidt_analysis', methods=['POST'])
@login_required
def edit_analysis():
    name = request.json['name']
    note = request.json['note']
    rd = request.json['round']
    id = request.json['id']  
    try:
        analysis = Analysis.query.get(id)
        rd = [int(i[6:]) for i in rd]
        analysis.name=name
        analysis.note=note
        analysis._rounds=rd 
        analysis.save_data()
        db.session.commit()
        return "Edit has been saved."
    except Exception as e:
        return f"Error: {e}"


@bp.route('/analysis_data/<path:filename>',methods=['GET'])
def analysis_data(filename):
    return send_from_directory(current_app.config['ANALYSIS_FOLDER'], filename, as_attachment=True)


@bp.route('/get_bar_progress', methods=['POST'])
@login_required
def get_bar_progress():
    ids = request.json['barlist']
    progresses = dict.fromkeys(ids)
    for id in ids:
        table, index = id.split(':')
        if table != 'task':
            indx = int(index)
        t = models_table_name_dictionary.get(table, None)
        if t:
            progress = t.query.get(index).progress
            progresses[id] = progress
    return jsonify(progresses)


@bp.route('/lev_search/<table>', methods=['GET'])
@login_required
def lev_search(table):
    task_id = request.args.get('task_id')
    page = request.args.get('page', 1, type=int)
    try:
        result = current_app.fetch_job_result(task_id)
    except:
        abort(404)
    target = {'sequence':SeqRound,'primer':Primers,'known_sequence':KnownSequence}.get(table)
    entries = []
    table = "sequence_round" if table =='sequence' else table
    for _id, _s in result:
        if table == 'sequence_round':
            entry = target.query.filter_by(sequence_id=_id).order_by(target.count.desc()).first()
        else:
            entry = target.query.get(_id)
        entry.lev_score = _s
        entries.append(entry)
    return render_template('ngs/sequence_search_result.html', title='Search-' + table, entries=entries,
                           table=table )


@bp.route('/get_selection_tree_json', methods=['POST'])
@login_required
def get_selection_tree_json():
    s_id = request.json.get('id')
    sele = Selection.query.get(s_id)
    # notes = sele.json_tree_notes()
    return jsonify(dict(tree=sele.json_tree(),))





@bp.route('/save_tree', methods=['POST'])
@login_required
def save_tree():
    try:
        tree = request.json['tree']
        sele = Selection.query.filter_by(id=tree['name'][3:]).first()
        tree = {'name': 'root', 'children':tree['children']}
        def dfs(tree):  
            yield tree     
            for v in tree.get('children',[]):
                for u in dfs(v):
                    yield u
        for i in dfs(tree):
            if i['name']!='root':
                parent = Rounds.query.filter_by(round_name=i['name'],selection_id=sele.id).first()
                children = Rounds.query.filter(Rounds.round_name.in_([j['name'] for j in  i.get('children', [])])).all()
                for child in children:
                    child.parent_id=parent.id
        db.session.commit()       
        messages = [('success','Selection tree saved.')]
    except Exception as e:
        messages = [('warning',f'Error occured during saving tree: <{e}>')]
    return jsonify(msg=messages[0])
