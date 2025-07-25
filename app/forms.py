from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,BooleanField,SubmitField,TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo,Length
import sqlalchemy as sa
from app import db
from app.models import User
from flask_babel import _, lazy_gettext as _l # Flask-Babel 提供了一个 _() 的惰性求值 (lazy evaluation) 版本，名为 lazy_gettext()
#一些字符串字面量是在网页请求之外被赋值的，通常是在应用启动时
#所以在这些文本被求值（evaluate）的时候，我们还无法知道应该使用哪种语言
#一个例子就是与表单字段关联的标签 (labels)
#处理这些文本的唯一解决方案是，找到一种方法来延迟 (delay) 这些字符串的求值，直到它们被使用时——那将会是在一个实际的请求中
#这个新函数将文本包裹在一个特殊的对象中，这个对象会触发翻译操作在稍后被执行，也就是当这个字符串在一个请求内部被使用时


class LoginForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))

class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(),
                                           EqualTo('password')])
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
        
class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    about_me = TextAreaField(_l('About me'),
                             validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

     # 1. 重载构造函数 (__init__)
    #    这个方法在创建一个 EditProfileForm 对象时被调用 (form = EditProfileForm(...))。
    #    它接收一个额外的参数 `original_username`。
    def __init__(self, original_username, *args, **kwargs):
        # 调用父类的构造函数，这是必须的。
        super().__init__(*args, **kwargs)
        # 将传入的原始用户名存储为这个表单实例的一个属性。
        self.original_username = original_username

    # 2. 自定义的验证方法 (validate_<field_name>)
    #    WTForms 有一个约定：任何以 `validate_<字段名>` 命名的方法，都会在标准验证器
    #    (如 DataRequired) 运行之后，被自动调用来对该字段进行额外的验证。
    def validate_username(self, username):
        # `username` 参数是表单中的 `username` 字段对象。
        # `username.data` 是用户在表单里输入的新值。
        
        # 3. 核心逻辑：只有当用户试图修改用户名时，才进行数据库检查。
        if username.data != self.original_username:
            # 去数据库里查找是否已经有用户使用了这个新的用户名。
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            # 如果找到了用户 (user is not None)，说明新用户名已被占用。
            if user is not None:
                # 抛出一个 ValidationError 异常，WTForms 会捕获它，
                # 并将异常中的消息附加到该字段的 .errors 列表中。
                raise ValidationError('Please use a different username.')

class EmptyForm(FlaskForm): # 使用空表单模型用于防止网络攻击
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    post = TextAreaField(_l('Say something'), validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))

class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Request Password Reset'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))