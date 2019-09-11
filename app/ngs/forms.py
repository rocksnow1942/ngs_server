from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField,TextAreaField,FieldList,FormField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo,Length,Optional
from app.models import Selection, Rounds, Primers, NGSSampleGroup
from app import db


class CheckName(FlaskForm):
    def __init__(self,old_name=None,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.old_name=old_name

class AddSelectionForm(CheckName):
    selection_name = StringField('Selection Name', validators=[
        DataRequired(), Length(min=0, max=100)], render_kw=dict(placeholder="Selection Name"))
    targetoptions = [('VEGF','VEGF'),('ANG2','ANG2')]
    target = SelectField('Selection Target', choices=targetoptions,
                         validators=[DataRequired(), Length(min=0, max=50)])
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder="Notes (Optional)"))
    submit = SubmitField('Confirm Add Selection')

    def validate_selection_name(self, selection_name):
        if selection_name.data != self.old_name:
            a = Selection.query.filter_by(selection_name=selection_name.data).first()
            if a is not None:
                raise ValidationError('Please use a different selection name.')

class AddRoundForm(CheckName):
    selection = StringField('Selection',validators=[DataRequired()],render_kw={'list':'selections','placeholder':'Selection'})
    round_name = StringField('Round Name', validators=[
        DataRequired(), Length(min=0, max=50)], render_kw=dict(placeholder='Round name'))
    target = StringField('Round Target', render_kw=dict(placeholder='Target name'),
                         validators=[DataRequired(), Length(min=0, max=50)])
    forward_primer = StringField('Forward Primer', validators=[DataRequired()], render_kw=dict(placeholder='forward primer', list="primers"))
    reverse_primer=StringField('Reverse Primer', validators = [DataRequired(
        )], render_kw = dict(placeholder='reverse primer', list="primers"))
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder='Notes (Optional)'))
    submit = SubmitField('Confirm Add Round')#render_kw={"class":"btn btn-secondary"}

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

class AddPrimerForm(CheckName):
    name = StringField('Primer Name', validators=[
        DataRequired(), Length(min=0, max=20)], render_kw=dict(placeholder='Primer Name'))
    sequence = StringField("Sequence 5'-3'", validators=[
        DataRequired(), Length(min=0, max=200)], render_kw=dict(placeholder="Primer Sequence, 5'-3'"))
    primeroptions = [('PD','PD'),('NGS','NGS'),('SELEX','SELEX'),('Other','Other')]
    role = SelectField('Primer type', choices = primeroptions, validators=[DataRequired()])
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder="Notes (Optional)"))
    submit = SubmitField('Confirm Add Primer')#render_kw={"class":"btn btn-secondary"}
    def validate_name(self,name):
        if name.data != self.old_name:
            if Primers.query.filter_by(name=name.data).first():
                raise ValidationError(
                    'Please use a different primer name.')

    def validate_sequence(self,sequence):
        seq=sequence.data.upper()
        if not (set(seq) <= set('ATCG')):
            raise ValidationError(
                "Only ATCG are allowed for primer")

class EditSelectionForm(AddSelectionForm):
    submit = SubmitField('Confirm Edit Selection')

class EditRoundForm(AddRoundForm):
    submit = SubmitField('Confirm Edit Round')

class EditPrimerForm(AddPrimerForm):
    submit = SubmitField('Confirm Edit Primer')



class AddSampleForm(FlaskForm):
    selection = StringField('Selection',validators=[DataRequired()],render_kw={'list':'selections','placeholder':'Selection'})

    round_id = SelectField('Round',choices=[],validators=[DataRequired()],coerce=int,render_kw={'placeholder':'Round'})

    fp_id = SelectField('FP Index',choices=[],validators=[DataRequired()],coerce=int,render_kw={'placeholder':'FP Index'})
    rp_id = SelectField('RP Index',choices=[],validators=[DataRequired()],coerce=int,render_kw={'placeholder':'RP Index'})
    class Meta:
        csrf = False

    def populate_obj(self,obj):
        return obj(round_id=self.round_id.data,fp_id=self.fp_id.data,rp_id=self.rp_id.data)


class AddSampleGroupForm(CheckName):
    name = StringField('Name', validators=[DataRequired()])
    note = TextAreaField('Notes', validators=[Length(
        min=0, max=300)], render_kw=dict(placeholder='Notes (Optional)'))

    samples = FieldList(FormField(AddSampleForm),min_entries=1)
    
    add_sample = SubmitField('Add another sample')
    submit = SubmitField('Save Samples')
    def validate_name(self,name):
        if name.data != self.old_name:
            if NGSSampleGroup.query.filter_by(name=name.data).first():
                raise ValidationError(
                    'Name {} is already used.'.format(name.data))

    def populate_obj(self,obj):
        return obj(name=self.name.data,note=self.note.data)
