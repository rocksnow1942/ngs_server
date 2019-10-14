from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired,ValidationError, Length
from app.models import User
from flask import request


class SearchNGSForm(FlaskForm):
    q = StringField('Search Keywords', validators=[DataRequired()])
    field = [('selection', 'Selection'), ('round', 'Rounds'),
             ('known_sequence', 'Aptamers'), ('analysis', 'Analysis'), ('ngs_sample_group', 'NGS Samples'),('primer','Primers'),('sequence','Sequence')]
    search_field = SelectField('Search In', choices=field, validators=[DataRequired()])
    method = [('text','Text Match'),('sequence','bp Match/Rev Comp'),('distance','Levenshtein Distance')]
    search_method= SelectField('Search Method', choices=method,validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchNGSForm, self).__init__(*args, **kwargs)


class SearchInventoryForm(FlaskForm):
    q = StringField('Search Inventory', validators=[DataRequired()])
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


class SearchPPTForm(FlaskForm):
    q = StringField('Search Keywords', validators=[DataRequired()])
    project = [('all', 'All'),]
    search_project = SelectField(
        'Search In Project', choices=project, validators=[DataRequired()])
    field = [('slide', 'Slide'), ('tag', 'Tag')]

    search_field = SelectField(
        'Search Field', choices=field, validators=[DataRequired()])

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
