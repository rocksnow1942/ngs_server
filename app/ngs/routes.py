from app import db
from flask import render_template, flash, redirect,url_for,request,current_app,abort,jsonify
from flask_login import current_user,login_required
from datetime import datetime
from app.ngs import bp
from app.models import Selection,Rounds,Primers,Sequence,SeqRound,NGSSampleGroup,NGSSample
from app.ngs.forms import AddSelectionForm, AddRoundForm,AddPrimerForm,EditPrimerForm,EditRoundForm,EditSelectionForm, AddSampleGroupForm
from sqlalchemy.exc import IntegrityError


@bp.route('/', methods=['GET', 'POST'])
@login_required
def ngs():
    return render_template('ngs/ngs.html',title='NGS')


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():

    return render_template('ngs/upload.html', title='Upload', form={'form': 'upload'})


@bp.route('/browse', methods=['GET', 'POST'])
@login_required
def browse():
    pagelimit = current_app.config['PAGE_LIMIT']
    content = request.args.get('content')
    id = request.args.get('id',0,type=int)
    page = request.args.get('page',1,type=int)
    target = {'selection':Selection,'round':Rounds,'sequence':SeqRound,'primer':Primers,'ngssample':NGSSampleGroup}.get(content,None)
    if target:
        if id:
            if content=='round':
                entries = target.query.filter_by(selection_id=id).order_by(target.id.desc()).paginate(page,pagelimit,False)

            elif content=='sequence':
                entries = target.query.filter_by(rounds_id=id).order_by(target.count.desc()).paginate(page,pagelimit,False)
                # entries = [SequenceDisplay(i.sequence,i.count,i.count/rd.totalread,rd.round_name) for i in r]
        else:
            entries = target.query.order_by(target.id.desc()).paginate(page,pagelimit,False)

        nextcontent = {'round':'sequence','selection':'round'}.get(content)
        kwargs={}
        if id: kwargs.update(id=id,nextcontent=nextcontent)
        next_url = url_for('ngs.browse',content=content,
                        page=entries.next_num,**kwargs) if entries.has_next else None
        prev_url = url_for('ngs.browse', content=content,
                        page=entries.prev_num,**kwargs) if entries.has_prev else None

        return render_template('ngs/browse.html', title='Browse' + (content or ' '), entries=entries.items,
                            next_url=next_url, prev_url=prev_url, content = content,nextcontent=nextcontent)
    return render_template('ngs/browse.html', title='Browse', entries=[],content='')


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """
    to do: add dynamic roundname and target option for adding rounds, based on selected selection.
    """
    toadd = request.args.get('toadd')
    if toadd == 'ngssample':
        return redirect(url_for('ngs.addsample'))
    datalist = {}
    if toadd == 'round':
        form = AddRoundForm()
        datalist.update(selections=db.session.query(
                Selection.selection_name).all(),
            primers=db.session.query(Primers.name).filter(
                Primers.role.in_(('SELEX', 'PD'))).all(),
                )
    elif toadd == 'primer' :
        form = AddPrimerForm()
    elif toadd == 'selection':
        form = AddSelectionForm()
    if form.validate_on_submit():
        if toadd == 'round':
            selection_id = Selection.query.filter_by(
                selection_name=form.selection.data).first().id
            fpid = Primers.query.filter_by(name=form.forward_primer.data).first().id
            rpid = Primers.query.filter_by(name=form.reverse_primer.data).first().id
            newitem = Rounds(selection_id=selection_id,
            round_name=form.round_name.data,target=form.target.data,note=form.note.data,
            forward_primer=fpid,reverse_primer=rpid)
        elif toadd == 'selection':
            newitem = Selection(selection_name=form.selection_name.data, target=form.target.data,
            note=form.note.data)
        elif toadd =='primer':
            newitem= Primers(name=form.name.data,sequence=form.sequence.data.upper(),role=form.role.data,note=form.note.data)
        db.session.add(newitem)
        db.session.commit()
        flash('New {} added.'.format(toadd), 'success')
        return redirect(url_for('ngs.add', toadd=toadd))
    return render_template('ngs/add.html', title='Add', toadd=toadd,form=form,datalist=datalist)


edit_redirect_url = "/"
@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    global edit_redirect_url
    if request.method == 'GET':
        edit_redirect_url = request.referrer or '/'
    toadd = request.args.get('toadd')
    id = request.args.get('id',1, type=int)
    datalist = {}
    if toadd == 'round':
        newitem = Rounds.query.get(id)
        form = EditRoundForm(newitem.round_name)
        datalist.update(selections=db.session.query(
                Selection.selection_name).all(),
            primers=db.session.query(Primers.name).filter(Primers.role.in_(('SELEX','PD'))).all(),)
        if  request.method == 'GET':
            form.selection.data = newitem.selection and newitem.selection.selection_name
            form.round_name.data = newitem.round_name
            form.target.data = newitem.target
            form.forward_primer.data = newitem.forward_primer and Primers.query.get(newitem.forward_primer).name
            form.reverse_primer.data = newitem.reverse_primer and Primers.query.get(newitem.reverse_primer).name
    elif toadd == 'primer' :
        newitem = Primers.query.get(id)
        form = EditPrimerForm(newitem.name)
        if  request.method == 'GET':
            form.name.data = newitem.name
            form.sequence.data=newitem.sequence
    elif toadd == 'selection':
        newitem = Selection.query.get(id)
        form = EditSelectionForm(newitem.selection_name)
        if  request.method == 'GET':
            form.selection_name.data = newitem.selection_name
            form.target = newitem.target
    else:
        return redirect(edit_redirect_url)

    if request.method == 'GET':
        form.note.data = newitem.note

    if form.validate_on_submit():
        if toadd == 'round':
            selection_id = Selection.query.filter_by(
                selection_name=form.selection.data).first().id
            fpid = Primers.query.filter_by(name=form.forward_primer.data).first().id
            rpid = Primers.query.filter_by(name=form.reverse_primer.data).first().id
            newitem.selection_id=selection_id
            newitem.round_name=form.round_name.data
            newitem.target=form.target.data
            newitem.forward_primer=fpid
            newitem.reverse_primer=rpid
        elif toadd == 'selection':
            newitem.selection_name=form.selection_name.data
            newitem.target=form.target.data
            newitem.note=form.note.data
        elif toadd =='primer':
            newitem.name=form.name.data
            newitem.sequence=form.sequence.data.upper()
            newitem.role=form.role.data
        newitem.note=form.note.data
        db.session.commit()
        flash('Your Edit to <{}> was saved.'.format(newitem),'success')
        return redirect(edit_redirect_url)
    return render_template('ngs/add.html', title='Edit', toadd=toadd,form=form,datalist=datalist)


@bp.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    global edit_redirect_url
    edit_redirect_url = request.referrer or '/'
    table = request.args.get('table')
    id = request.args.get('todelete',0,int)
    if table in ['selection','round','primer','ngs_sample_group']:
        target = {'selection':Selection,'round':Rounds,'primer':Primers,'ngs_sample_group':NGSSampleGroup}.get(table)
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
    form = AddSampleGroupForm()
    datalist={}
    datalist.update(selections=db.session.query(Selection.selection_name).all(),)
    plist = [(i.id,i.name) for i in Primers.query.filter_by(role='NGS').all()]
    rdlist = [(i.id,i.round_name) for i in Rounds.query.all()]
    for f in form.samples:
        f.form.fp_id.choices= plist
        f.form.rp_id.choices= plist
        f.form.round_id.choices = rdlist
    if request.method == 'POST':
        # check if all fp an rp index are unique.
        indextuple = []
        for i in form.samples:
            indextuple.append((i.form.fp_id.data,i.form.rp_id.data))
        if len(set(indextuple)) != len(indextuple):
            flash('Error: FP RP Index have duplicates. Check Primers.','danger')
            return render_template('ngs/editsample.html',title='Add',form=form,toadd='Sample',datalist=datalist)
        sg = form.populate_obj(NGSSampleGroup)
        for i in form.samples:
            sg.samples.append(i.form.populate_obj(NGSSample))
        db.session.add(sg)
        db.session.commit()
        flash('<{}> was added.'.format(sg),'info')
        return redirect(url_for('ngs.addsample'))

    return render_template('ngs/editsample.html',title='Add',form=form,toadd='Sample',datalist=datalist)


@bp.route('/add_extrasample', methods=[ 'POST'])
@login_required
def add_extrasample():
    form = AddSampleGroupForm()
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
    form = AddSampleGroupForm()
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

@bp.route('/get_bar_progress', methods=['POST'])
@login_required
def get_bar_progress():
    ids = request.json['barlist']
    progresses = dict.fromkeys(ids)
    tablenames = {'ngs_sample_group':NGSSampleGroup}
    for id in ids:
        table,index = id.split('-')
        t = tablenames.get(table,None)
        if t:
            progress = t.query.get(int(index)).progress
            progresses[id] = progress
    return jsonify(progresses)


@bp.route('/details', methods=['GET', 'POST'])
@login_required
def details():
    abort(404)
