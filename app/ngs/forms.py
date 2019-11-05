from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField,TextAreaField,FieldList,FormField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo,Length,Optional
from app.models import Selection, Rounds, Primers, NGSSampleGroup, NGSSample, KnownSequence, SeqRound, Sequence
from app import db


ngs_edit_form_dictionary = {}
ngs_add_form_dictionary = {}

def register_add_form(cls):
    global ngs_add_form_dictionary
    ngs_add_form_dictionary.update({cls.__name__[:-4].lower(): cls})
    return cls


def register_edit_form(cls):
    global ngs_edit_form_dictionary
    ngs_edit_form_dictionary.update({cls.__name__[:-5].lower(): cls})
    return cls

class CheckName(FlaskForm):
    def __init__(self,old_obj=None,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.old_name=old_obj and old_obj.name
        

@register_add_form
class Selection_Add(CheckName):
    selection_name = StringField('Selection Name', validators=[
        DataRequired(), Length(min=0, max=100)], render_kw=dict(placeholder="Selection Name"))
    targetoptions = [('VEGF','VEGF'),('ANG2','ANG2')]
    target = StringField('Selection Target', validators=[
        DataRequired(), Length(min=0, max=50)], render_kw=dict(placeholder="Selection Target",list='targets'))
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder="Notes (Optional)"))
    submit = SubmitField('Confirm Add Selection')

    def load_obj(self,id=0):
        newitem = Selection.query.get(id)
        if newitem:
            form = self
            form.selection_name.data = newitem.selection_name
            form.target.data = newitem.target
            form.note.data = newitem.note

    def populate_obj(self,id=0):
        newitem = Selection.query.get(id)
        form=self
        if newitem:
            newitem.selection_name = form.selection_name.data
            newitem.target = form.target.data
            newitem.note = form.note.data
            return newitem
        else:
            return Selection(selection_name=form.selection_name.data, target=form.target.data,
                            note=form.note.data)

    def validate_selection_name(self, selection_name):
        if selection_name.data != self.old_name:
            a = Selection.query.filter_by(selection_name=selection_name.data).first()
            if a is not None:
                raise ValidationError('Please use a different selection name.')


@register_add_form
class Round_Add(CheckName):
    selection = StringField('Selection',validators=[DataRequired()],render_kw={'list':'selections','placeholder':'Selection'})
    round_name = StringField('Round Name', validators=[
        DataRequired(), Length(min=0, max=50)], render_kw=dict(placeholder='Round name', list='rounds'))
    parent = StringField('Parent Round', render_kw=dict(placeholder='Parent Round Name', list='rounds'),
                         validators=[Length(min=0, max=50)])
    target = StringField('Round Target', render_kw=dict(placeholder='Target name', list='targets'),
                         validators=[DataRequired(), Length(min=0, max=50)])
    
    forward_primer = StringField('Forward Primer', validators=[DataRequired()], render_kw=dict(placeholder='forward primer', list="primers"))
    reverse_primer=StringField('Reverse Primer', validators = [DataRequired(
        )], render_kw = dict(placeholder='reverse primer', list="primers"))
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder='Notes (Optional)'))
    submit = SubmitField('Confirm Add Round')#render_kw={"class":"btn btn-secondary"}

    def load_obj(self,id=0):
        newitem = Rounds.query.get(id)
        if newitem:
            form=self
            form.selection.data = newitem.selection and newitem.selection.selection_name
            form.round_name.data = newitem.round_name
            form.parent.data = newitem.parent_id and newitem.parent.round_name
            form.target.data = newitem.target
            form.forward_primer.data = newitem.forward_primer and newitem.FP.name
            form.reverse_primer.data = newitem.reverse_primer and newitem.RP.name
            form.note.data = newitem.note 


    def populate_obj(self,id=0):
        rd = Rounds.query.get(id)
        form=self
        selection_id = Selection.query.filter_by(
            selection_name=form.selection.data).first().id
        fpid = Primers.query.filter_by(
            name=form.forward_primer.data).first().id
        rpid = Primers.query.filter_by(
            name=form.reverse_primer.data).first().id
        parent = Rounds.query.filter_by(
            round_name=form.parent.data.strip()).first()
        parent_id = parent and parent.id
        
        if not rd: rd = Rounds()
        rd.selection_id=selection_id
        rd.round_name = form.round_name.data.strip()
        rd.target = form.target.data
        rd.note = form.note.data
        rd.forward_primer=fpid
        rd.reverse_primer = rpid
        rd.parent_id = parent_id
        return rd
        

    def validate_parent(self,parent):
        if parent.data.strip():
            par = Rounds.query.filter_by(round_name=parent.data.strip()).first()
            if not par:
                raise ValidationError(
                    'Round <{}> is not created.'.format(parent.data))
            if self.round_name.data.strip() == parent.data.strip():
                raise ValidationError(
                    'Round <{}> can\'t be its own parent.'.format(parent.data))
            if par.parent and par.parent.round_name == self.round_name.data.strip():
                raise ValidationError(
                    "Round <{}>'s parent is Round <{}>.".format(parent.data,self.round_name.data))


            

    def validate_selection(self,selection):
        if not Selection.query.filter_by(selection_name=selection.data).first():
            raise ValidationError('Selection <{}> is not created.'.format(selection.data))

    def validate_round_name(self,round_name):
        s=Selection.query.filter_by(selection_name=self.selection.data).first()
        s = s.id if s else 0
        if round_name.data!=self.old_name:
            if Rounds.query.filter_by(selection_id=s,round_name=round_name.data).first():
                raise ValidationError('Name <{}> in <{}> already taken.'.format(round_name.data,self.selection.data))

    def validate_forward_primer(self,forward_primer):
        self.validateprimer(forward_primer)

    def validate_reverse_primer(self,reverse_primer):
        self.validateprimer(reverse_primer)

    def validateprimer(self,primer):
        p = Primers.query.filter_by(name=primer.data).first()
        if not p:
            raise ValidationError(
                'Primer <{}> is not created.'.format(primer.data))


@register_add_form
class Primer_Add(CheckName):
    name = StringField('Primer Name', validators=[
        DataRequired(), Length(min=0, max=20)], render_kw=dict(placeholder='Primer Name'))
    sequence = StringField("Sequence 5'-3'", validators=[
        DataRequired(), Length(min=0, max=200)], render_kw=dict(placeholder="Primer Sequence, 5'-3'"))
    primeroptions = [('PD','PD'),('NGS','NGS'),('SELEX','SELEX'),('Other','Other')]
    role = SelectField('Primer type', choices = primeroptions, validators=[DataRequired()])
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder="Notes (Optional)"))
    submit = SubmitField('Confirm Add Primer')#render_kw={"class":"btn btn-secondary"}
    
    def load_obj(self,id=0):
        newitem = Primers.query.get(id)
        if newitem:
            self.name.data = newitem.name
            self.sequence.data = newitem.sequence
            self.role.data = newitem.role
            self.note.data = newitem.note
    def populate_obj(self,id=0):
        newitem = Primers.query.get(id)
        if not newitem:
            newitem = Primers()
        newitem.name = self.name.data
        newitem.sequence = self.sequence.data.upper().strip()
        newitem.role = self.role.data
        newitem.note = self.note.data
        return newitem
    
       
    def validate_name(self,name):
        if name.data != self.old_name:
            if Primers.query.filter_by(name=name.data).first():
                raise ValidationError(
                    'Please use a different primer name.')

    def validate_sequence(self,sequence):
        seq=sequence.data.upper().strip()
        if not (set(seq) <= set('ATCG')):
            raise ValidationError(
                "Only ATCG are allowed for primer")


@register_add_form
class Known_Sequence_Add(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired(), Length(min=0, max=50)], render_kw=dict(placeholder='Sequence Name'))
    sequence = StringField("Sequence 5'-3'", validators=[
        DataRequired(), Length(min=0, max=200)], render_kw=dict(placeholder="Sequence, 5'-3'"))
    target = StringField("Target", validators=[
        DataRequired(), Length(min=0, max=50)], render_kw=dict(placeholder="Target"))
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder="Notes (Optional)"))
    submit = SubmitField('Confirm Add Known Sequence')
    
    def __init__(self, old_obj=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = old_obj and old_obj.sequence_name
        self.old_sequence = old_obj and old_obj.rep_seq


    def load_obj(self, id=0):
        newitem = KnownSequence.query.get(id)
        if newitem:
            self.name.data = newitem.sequence_name
            self.sequence.data = newitem.rep_seq
            self.target.data = newitem.target
            self.note.data = newitem.note

    def populate_obj(self, id=0):
        newitem = KnownSequence.query.get(id)
        if not newitem:
            newitem = KnownSequence()
        newitem.sequence_name = self.name.data
        newitem.target= self.target.data
        newitem.rep_seq = self.sequence.data.upper().strip()
        newitem.note = self.note.data
        if newitem.rep_seq != self.old_sequence:
            db.session.add(newitem)
            self.match_known_sequence(newitem)
        return newitem
    
    def match_known_sequence(self,ks):
        oldseq = Sequence.query.filter_by(knownas=ks).all()
        if oldseq:
            for i in oldseq:
                i.known_sequence_id = None
        tochange = Sequence.query.filter_by(aptamer_seq=ks.rep_seq).first()
        if tochange:
            tochange.knownas = ks
        
           

    def validate_name(self, name):
        if name.data != self.old_name:
            if KnownSequence.query.filter_by(sequence_name=name.data).first():
                raise ValidationError(
                    'Please use a different sequence name.')

    def validate_sequence(self, sequence):
        seq = sequence.data.upper().strip()
        if not (set(seq) <= set('ATCG')):
            raise ValidationError(
                "Only ATCG are allowed for sequence!")
        if seq != self.old_sequence:
            al = KnownSequence.query.filter_by(rep_seq=seq).first()
            if al:
                raise ValidationError('This sequence is already curated as <{}>.'.format(al))
    

@register_edit_form
class Sequence_Round_Edit(FlaskForm):
    rd = StringField('Round', render_kw=dict(disabled=''))
    ct = StringField('Count', render_kw=dict(disabled=''))
    sequence = StringField('Sequence',render_kw=dict(disabled=''))
    ks_sequence = StringField('Known As Sequence', render_kw=dict(disabled=''))
    knownas = StringField('Known As', render_kw=dict(placeholder='Parent Round Name', list='known_sequence'),
                          validators=[Length(min=0, max=50)])
    note = StringField('Note',render_kw=dict(placeholder='Note, (Optional)'))
                          
    submit = SubmitField('Confirm Edit Sequence')

    def __init__(self, old_obj=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    
    def load_obj(self,id):
        sr = SeqRound.query.get(id)
        if sr:
            self.sequence.data = sr.sequence.aptamer_seq
            self.rd.data = sr.round.round_name
            self.ct.data = sr.count
            self.knownas.data = sr.sequence.knownas and sr.sequence.knownas.sequence_name
            self.ks_sequence.data = sr.sequence.knownas and sr.sequence.knownas.rep_seq
            self.note.data = sr.sequence.note 

    def populate_obj(self,id):
        sr = SeqRound.query.get(id)
        ks = KnownSequence.query.filter_by(sequence_name=self.knownas.data).first()
        if sr:
            sq = sr.sequence
            sq.knownas = ks
            sq.note = self.note.data
    
    def validate_knownas(self,knownas):
        if knownas.data == '':
            return 0
        ks = KnownSequence.query.filter_by(
            sequence_name=knownas.data).first()
        if not ks:
            raise ValidationError('Aptamer {} is not created.'.format(knownas.data))

            

@register_edit_form
class Selection_Edit(Selection_Add):
    submit = SubmitField('Confirm Edit Selection')


@register_edit_form
class Round_Edit(Round_Add):
    submit = SubmitField('Confirm Edit Round')


@register_edit_form
class Primer_Edit(Primer_Add):
    submit = SubmitField('Confirm Edit Primer')


@register_edit_form
class Known_Sequence_Edit(Known_Sequence_Add):
    submit = SubmitField('Confirm Edit Known Sequence')


class AddSampleForm(FlaskForm):
    selection = StringField('Selection',validators=[DataRequired()],render_kw={'list':'selections','placeholder':'Selection'})

    round_id = SelectField('Round',validators=[DataRequired()],coerce=int,render_kw={'placeholder':'Round'})

    fp_id = SelectField('FP Index',validators=[DataRequired()],coerce=int,render_kw={'placeholder':'FP Index'})
    rp_id = SelectField('RP Index', validators=[DataRequired()],coerce=int,render_kw={'placeholder':'RP Index'})
    class Meta:
        csrf = False

    def populate_obj(self,obj):
        return obj(round_id=self.round_id.data,fp_id=self.fp_id.data,rp_id=self.rp_id.data)




@register_add_form
class NGS_Sample_Group_Add(CheckName):
    name = StringField('Name', validators=[DataRequired()])
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder='Notes (Optional)'))

    samples = FieldList(FormField(AddSampleForm),min_entries=1)
    ignore_duplicate = BooleanField('Ignore Duplicate')
    add_sample = SubmitField('Add another sample')
    submit = SubmitField('Save Samples')
    def validate_name(self,name=None):
        if name.data != self.old_name:
            if NGSSampleGroup.query.filter_by(name=name.data).first():
                raise ValidationError(
                    'Name < {} > already used.'.format(name.data))
                
    
    def validate_round(self,rd=None):
        if (self.ignore_duplicate.data):
            return None
        rounds = [i.form.round_id.data for i in self.samples]
        rd = Rounds.query.filter(Rounds.id.in_(rounds)).all()
        sequenced = [i for i in rd if i.sequenced]
        return [i.round_name for i in sequenced]
        

    def populate_obj(self,obj,id=0):
        nsg = NGSSampleGroup.query.get(id)
        if nsg:
            nsg.name= self.name.data 
            nsg.note = self.note.data
            nsg.samples = []
            return nsg
        else:
            return obj(name=self.name.data,note=self.note.data)
    
    def load_obj(self,id):
        """
        load obj into form.
        """
        nsg = NGSSampleGroup.query.get(id)
        if nsg:
            self.name.data=nsg.name
            self.note.data=nsg.note 
            self.samples.pop_entry()
            samples = NGSSample.query.filter_by(sample_group_id=id).all()
            for s in samples:
                self.samples.append_entry()
                sele = Rounds.query.get(s.round_id).selection.selection_name
                self.samples[-1].round_id.data = s.round_id 
                self.samples[-1].selection.data = sele
                self.samples[-1].fp_id.data = s.fp_id 
                self.samples[-1].rp_id.data = s.rp_id 



