from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, SelectMultipleField,IntegerField,DateField
from wtforms.validators import DataRequired,ValidationError, Length,NumberRange
from app.models import User
from flask import request
from datetime import datetime,timedelta


class SearchNGSForm(FlaskForm):
    q = StringField('Search Keywords', validators=[DataRequired()])
    field = [('selection', 'Selection'), ('round', 'Rounds'),
             ('known_sequence', 'Aptamers'), ('analysis', 'Analysis'), ('ngs_sample_group', 'NGS Samples'),('primer','Primers'),('sequence','Sequence')]
    search_field = SelectField('Search In', choices=field, validators=[DataRequired()])
    method = [('name','Name Match'),('text','Elastic Text Search'),('sequence','basepair Match/Rev Comp'),('distance','Levenshtein Distance')]
    search_method= SelectField('Search Method', choices=method,validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchNGSForm, self).__init__(*args, **kwargs)



class SearchPPTForm(FlaskForm):
    q = StringField('Search Keywords',)
    
    search_project = SelectMultipleField(
        'Search In Project', choices=[('all', 'All')], validators=[DataRequired()])  # choices=project
    field = [('all', 'All'), ('title', 'Title'),
             ('body', 'Body'), ('flag', 'Flag: Red Green Blue'), ('tag', 'Tag'), ('note', 'Note'), ]
    search_field = SelectMultipleField(
        'Search Field', choices=field, validators=[DataRequired()])
    search_ppt = SelectMultipleField(
        'Search In PPT', validators=[DataRequired()])
    date_from = DateField("From Date", default=(datetime(2011,1,1)).strftime('%Y-%m-%d'),format='%Y-%m-%d')
    date_to = DateField("To Date", default=datetime.now().strftime('%Y-%m-%d'), format='%Y-%m-%d')

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchPPTForm, self).__init__(*args, **kwargs)
        
        


class TestForm(FlaskForm):
    q = StringField('Mock Search', validators=[DataRequired()])
    field = [('selection', 'Selection'), ('round', 'Rounds'),
             ('known_sequence', 'APtamers'), ('analysis', 'Analysis')]
    search_field = SelectField(
        'Search In', choices=field, validators=[DataRequired()])
    method = [('text', 'Text'), ('sequence', 'DNA/RNA'),
              ('distance', 'Distance (SLOW)')]
    search_method = SelectField(
        'Search Method', choices=method, validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super().__init__(*args, **kwargs)

class UserSettingForm(FlaskForm):
    ngs_per_page = IntegerField('List Item Per Page', validators=[DataRequired(),NumberRange(3, 200)])
    slide_per_page = IntegerField('Slides Per Page', validators=[
                                  DataRequired(), NumberRange(3, 200)])
    thumbnail = SelectField('Default Thumbnail Size',choices=[('small','Small'),('medium','Medium'),('large','Large'),('list','List')])
    submit = SubmitField('Save Settings')
    
    def populate_obj(self,user):
        user.user_setting.update(ngs_per_page=self.ngs_per_page.data)
        user.user_setting.update(slide_per_page=self.slide_per_page.data)
        user.user_setting.update(thumbnail=self.thumbnail.data)
        user.save_data()
        return user
