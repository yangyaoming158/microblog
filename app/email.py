from flask_mail import Message
from app import mail,app
from flask import render_template

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)

def send_password_reset_email(user): # 发送重置密码的链接给用户邮箱
    token = user.get_reset_password_token()# 为一个用户实例生成一个有时效性的密码重置令牌。
    send_email('[Microblog] Reset Your Password',
               sender=app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt', # 发送的内容
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))