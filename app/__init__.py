
# 这个 __init__.py 文件完美地展示了应用工厂模式的精髓：
# 解耦 (Decoupling): 扩展对象 (db, login 等) 的创建和初始化 (绑定到 app) 被分离开来。这彻底解决了循环导入问题，因为任何模块现在都可以安全地 from app import db 而无需担心 app 实例是否已创建。
# 可配置性 (Configurability): create_app 函数可以接收一个配置类作为参数，这使得为不同环境（开发、测试、生产）创建使用不同配置的应用实例变得极其简单。
# 模块化 (Modularity): 应用的所有功能都被组织在不同的蓝图 (Blueprints) 中，然后在工厂函数内部进行统一的“组装”。这使得代码结构清晰，功能边界明确。
# 集中初始化: 所有与应用相关的初始化工作（绑定扩展、注册蓝图、配置日志）都集中在 create_app 这个函数里，一目了然。
import markdown
import bleach
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_babel import Babel, lazy_gettext as _l
from config import get_config_class
from elasticsearch import Elasticsearch


# --- 第一步：在全局范围创建【未绑定】的扩展实例 ---
# 在这里创建扩展对象，但不传入 app 实例。
# 这样做可以避免在其他模块（如蓝图）导入这些对象时产生循环依赖。
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'  # 指定登录页面的端点，用于 @login_required
login.login_message = _l('Please log in to access this page.') # 自定义登录提示消息，并使用惰性翻译
mail = Mail()
moment = Moment()
babel = Babel()

# --- 第二步：创建【应用工厂函数】---
# 这是组织 Flask 应用的最佳实践。
def create_app(config_class=None):
    """Create a configured Flask application instance."""
    app = Flask(__name__)
    if config_class is None:
        config_class = get_config_class()
    elif isinstance(config_class, str):
        config_class = get_config_class(config_class)

    if hasattr(config_class, 'validate'):
        config_class.validate()
    app.config.from_object(config_class)

    # b. 使用 .init_app() 方法，将上面创建的扩展实例与 app 实例进行绑定
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    babel.init_app(app,locale_selector=get_locale) # Babel 的 locale_selector 在外部通过装饰器注册
    # 在应用工厂模式下，如何处理那些没有 init_app() 方法的、非 Flask 扩展的第三方库？
    # elasticsearch 这个库不是一个 Flask 扩展，它没有 init_app() 这个方法
    # 它的实例 es = Elasticsearch(...) 在创建时必须立刻拿到 app.config 里的 URL
    # 不能在全局范围创建它，因为那时 app.config 还不存在
    # 在 create_app 函数内部创建 Elasticsearch 的实例后，直接把它当作一个新的属性，“挂”在 app 对象上
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None
    
    app.jinja_env.filters['markdown'] = format_markdown

    # c. 在函数内部，导入并注册蓝图 (Blueprints)
    #    将应用的不同功能模块化
    
    # 注册错误处理蓝图
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    # 注册用户认证蓝图，并为其所有路由添加 '/auth' URL 前缀
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # 注册核心功能蓝图 (主页、个人资料等)
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # 注册自定义命令行命令蓝图
    from app.cli import bp as cli_bp
    app.register_blueprint(cli_bp)

    # d. 配置日志系统 (只在非调试模式和非测试模式下启用)
    if not app.debug and not app.testing:
        # --- 配置邮件错误日志处理器 ---
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Microblog Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR) # 只在发生 ERROR 级别错误时发送邮件
            app.logger.addHandler(mail_handler)

        # --- 配置文件日志处理器 ---
        if not os.path.exists('logs'):
            os.mkdir('logs')
        # RotatingFileHandler 可以限制日志文件的大小，并进行备份，防止日志文件无限增大
        file_handler = RotatingFileHandler('logs/microblog.log',
                                           maxBytes=10240, backupCount=10)
        # 定义日志的格式
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO) # 记录 INFO 级别及以上的日志
        app.logger.addHandler(file_handler)

        # 设置应用日志的最低记录级别
        app.logger.setLevel(logging.INFO)
        # 记录一条应用启动信息
        app.logger.info('Microblog startup')

    # e. 返回创建好的应用实例
    return app

# --- 第三步：定义 Babel 的语言选择器函数 ---
# 它会在每个请求开始时被调用，以确定该使用哪种语言。
def get_locale():
    # request.accept_languages 是一个解析了浏览器 Accept-Language 请求头的对象。
    # .best_match() 会在浏览器提供的语言偏好列表和我们应用支持的语言列表之间，
    # 找到最佳的匹配项。
    # 使用 current_app 是因为这个函数在请求上下文中被调用。
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

def format_markdown(text):
    # 1. 将 Markdown 转为 HTML
    #    fenced_code: 支持 ``` 代码块
    #    tables: 支持表格
    allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                    'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                    'h1', 'h2', 'h3', 'p', 'img', 'br', 'span', 'div']
    
    # 允许的属性 (比如 img 的 src, a 的 href)
    allowed_attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['src', 'alt', 'title'],
    }

    html = markdown.markdown(text, extensions=['fenced_code', 'tables'])
    
    # 2. 【关键】使用 Bleach 清洗 HTML，防止 XSS 攻击
    #    这一点至关重要！否则用户可以输入 <script>alert(1)</script> 来攻击你的网站。
    clean_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)
    
    return clean_html

# --- 第四步：在文件底部导入 models 模块 ---
# 这一步的目的是为了让 SQLAlchemy 能够发现我们的模型类。
# 因为 models.py 需要导入在上面定义的全局 'db' 对象，所以这个导入必须放在 'db' 定义之后。
from app import models