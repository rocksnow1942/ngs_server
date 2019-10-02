from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired,ValidationError,Email, EqualTo
from app.models import User



class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    loginsubmit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(),Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password',validators=[DataRequired(),
                         EqualTo('password')])
    submit = SubmitField('Register')

    def __init__(self, old_obj=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = old_obj and old_obj.username
        self.old_email = old_obj and old_obj.email

    def validate_username(self, username):
        if self.old_name != username.data:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Please use a different user name.')

    def validate_email(self, email):
        if self.old_email != email.data:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Please use a different email address.')


class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit=SubmitField('Save Changes')
    def __init__(self, old_obj=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = old_obj and old_obj.username
        self.old_email = old_obj and old_obj.email

    def load_obj(self,user):
        self.username.data=user.username
        self.email.data = user.email
    

    def validate_username(self,username):
        if self.old_name != username.data:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Please use a different user name.')

    def validate_email(self, email):
        if self.old_email != email.data:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Please use a different email address.')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(),Email()])
    submit = SubmitField('Request Password Reset')

class ResetPassWordForm(FlaskForm):
    password = PasswordField('Password',validators=[DataRequired()])
    password2 = PasswordField('Repeat password', validators=[DataRequired(),EqualTo('password')])
    submit = SubmitField('Request Password Reset')


class InviteNewUser(FlaskForm):
    username = StringField('New User Name', validators=[DataRequired()])
    email = StringField('New User Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Invitation')

    def validate_email(self,email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('This email is already registered.')

