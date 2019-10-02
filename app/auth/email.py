from app.email import send_email
from flask import render_template, current_app



def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Aptitude Server] Reset your password',
            sender=current_app.config['ADMINS'][0],
            recipients=[user.email],
            text_body=render_template('email/reset_password.txt',user=user,token=token),
            html_body=render_template('email/reset_password.html',user=user,token=token))


def send_invitation_email(user):
    token = user.get_reset_password_token(expires_in=3600*12)
    send_email('You are invited to join [Aptitude Server]',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(
                   'email/invite_user.txt', user=user, token=token),
               html_body=render_template('email/invite_user.html', user=user, token=token))
