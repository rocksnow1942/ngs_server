from app import db
from flask import render_template, flash, redirect,url_for,request
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPassWordForm, ProfileForm, InviteNewUser
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse
from app.auth.email import send_password_reset_email, send_invitation_email
from app.auth import bp

@bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'warning')
            return redirect(url_for('auth.login'))
        login_user(user,remember=form.remember_me.data)
        next_page= request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)

    return render_template('auth/login.html',title='Sign In', form=form)


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form=ProfileForm(old_obj=current_user,obj=current_user)
    
    if form.validate_on_submit():
        current_user.username=form.username.data
        current_user.email=form.email.data
        db.session.commit()
        flash('Your changes were saved.','success')
        return redirect(url_for('main.index'))
    return render_template('auth/profile.html', user=current_user, title='Profile', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register/<token>',methods=['GET','POST'])
def register(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = RegistrationForm(old_obj=user,obj=user)
    if form.validate_on_submit():
        user.username=form.username.data 
        user.emal=form.email.data
        user.set_password(form.password.data)
        db.session.commit()
        flash('Congrats, you are now registered. Please log in.','info')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html',title='Register',form=form)



@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password.','info')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_request.html',title='Reset Password',form=form)


@bp.route('/create_newuser', methods=['GET', 'POST'])
@login_required
def create_newuser():
    if not current_user.isadmin:
        return redirect(url_for('main.index'))
    form = InviteNewUser()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None:
            user.username=form.username.data
        else:
            user = User(email=form.email.data,username=form.username.data)
            db.session.add(user)
        db.session.commit()
        send_invitation_email(user)
        flash('New user added.', 'info')
        return redirect(url_for('admin.admin'))
    return render_template('auth/reset_password_request.html', title='Invite New user', form=form)


@bp.route('/reset_password/<token>',methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPassWordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.','success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html',form=form)
