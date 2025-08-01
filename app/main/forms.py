from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length
import sqlalchemy as sa
from flask_babel import _, lazy_gettext as _l
from app import db
from app.models import User
from flask import request


class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
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


class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    post = TextAreaField(_l('Say something'), validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))


class SearchForm(FlaskForm):
    """
    一个专门用于处理 GET 请求的全局搜索表单。
    """
    # 1. 定义表单字段
    #    - q: 这是字段的变量名。'q' (query) 是搜索引擎 URL 参数的通用约定。
    #    - StringField: 这是一个单行的文本输入框。
    #    - _l('Search'): 字段的标签 (label)。使用惰性翻译，因为它是在应用启动时定义的。
    #    - validators=[DataRequired()]: 添加一个验证器，确保用户不能提交空的搜索。
    q = StringField(_l('Search'), validators=[DataRequired()])

    # 2. 【核心】重载构造函数 (__init__)
    #    - 这个方法在创建一个 SearchForm 实例时被自动调用 (例如: form = SearchForm())。
    #    - 我们重载它，是为了在表单被创建时，动态地修改它的默认行为。
    def __init__(self, *args, **kwargs):
        # a. 【关键技巧 #1】修改表单数据的来源
        #    - WTForms 默认从 `request.form` 中获取提交的数据，
        #      而 `request.form` 只包含 POST 请求的数据。
        #    - 我们需要的数据在 URL 的查询字符串中，Flask 将其存储在 `request.args` 里。
        if 'formdata' not in kwargs:
            # - 检查调用者是否已经手动提供了 formdata。如果没有...
            # - 我们就自己提供一个，明确告诉 WTForms：“请从 request.args 里找数据！”
            kwargs['formdata'] = request.args
        
        # b. 【关键技巧 #2】禁用 CSRF 保护
        #    - Flask-WTF 默认会为所有表单开启 CSRF 保护，这要求 POST 请求
        #      并且模板中有 `form.hidden_tag()`。
        #    - 对于一个通过 GET 请求提交的、公开的搜索功能，CSRF 保护是不必要的，
        #      而且会阻止用户直接通过 URL (如 /search?q=python) 进行搜索。
        if 'meta' not in kwargs:
            # - 检查调用者是否已经手动配置了 meta。如果没有...
            # - 我们就自己提供一个，将 'csrf' 键设置为 False，从而禁用 CSRF 验证。
            kwargs['meta'] = {'csrf': False}
        
        # c. 调用父类的构造函数
        #    - 在完成了我们的自定义修改后，必须调用父类 (FlaskForm) 的 `__init__` 方法，
        #      并将所有参数 (包括我们修改过的 kwargs) 传递给它，
        #      以完成表单的标准初始化流程。
        super(SearchForm, self).__init__(*args, **kwargs)

class CommentForm(FlaskForm):
    body = TextAreaField(_l('Comment'), validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))