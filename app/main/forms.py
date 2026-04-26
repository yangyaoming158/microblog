from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length, Regexp
import sqlalchemy as sa
from flask_babel import _, lazy_gettext as _l
from app import db
from app.models import User
from flask import request

USERNAME_VALIDATORS = [
    DataRequired(),
    Length(min=3, max=64),
    Regexp(
        r'^[A-Za-z][A-Za-z0-9_.-]*$',
        message=_l('Usernames must start with a letter and contain only letters, numbers, dots, underscores, or hyphens.')
    ),
]


class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=USERNAME_VALIDATORS)
    about_me = TextAreaField(_l('About me'),
                             validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            if user is not None:
                raise ValidationError(_('Please use a different username.'))


class ChangeAvatarForm(FlaskForm):
    avatar = FileField(_l('New Avatar'), validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], _l('Images only.'))
    ])
    submit = SubmitField(_l('Upload'))


class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    title = StringField(_l('Title'), validators=[DataRequired(), Length(min=5, max=30)])
    post = TextAreaField(_l('Say something'), validators=[
        DataRequired(), Length(min=1, max=5000)])
    submit = SubmitField(_l('Submit'))


class SearchForm(FlaskForm):
    q = StringField(_l('Search'), validators=[DataRequired(), Length(min=1, max=100)])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'meta' not in kwargs:
            kwargs['meta'] = {'csrf': False}
        super(SearchForm, self).__init__(*args, **kwargs)


class CommentForm(FlaskForm):
    body = TextAreaField(_l('Comment'), validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))


class MessageForm(FlaskForm):
    message = TextAreaField(_l('Message'), validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))