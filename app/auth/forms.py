from flask_wtf import FlaskForm
from flask_babel import _, lazy_gettext as _l
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (
    ValidationError, DataRequired, Email, EqualTo, Length, Regexp
)
import sqlalchemy as sa
from app import db
from app.models import User

USERNAME_VALIDATORS = [
    DataRequired(),
    Length(min=3, max=64),
    Regexp(
        r'^[A-Za-z][A-Za-z0-9_.-]*$',
        message=_l('Usernames must start with a letter and contain only letters, numbers, dots, underscores, or hyphens.')
    ),
]
PASSWORD_VALIDATORS = [
    DataRequired(),
    Length(min=8, max=128),
]


class LoginForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired(), Length(max=64)])
    password = PasswordField(_l('Password'), validators=[DataRequired(), Length(max=128)])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))


class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=USERNAME_VALIDATORS)
    email = StringField(_l('Email'), validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(_l('Password'), validators=PASSWORD_VALIDATORS)
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l('Register'))

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(
            User.username == username.data))
        if user is not None:
            raise ValidationError(_('Please use a different username.'))

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data))
        if user is not None:
            raise ValidationError(_('Please use a different email address.'))


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField(_l('Request Password Reset'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=PASSWORD_VALIDATORS)
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l('Current Password'), validators=[DataRequired(), Length(max=128)])
    password = PasswordField(_l('New Password'), validators=PASSWORD_VALIDATORS)
    password2 = PasswordField(
        _l('Repeat New Password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l('Update Password'))