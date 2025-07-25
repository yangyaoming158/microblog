import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')or'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI =os.environ.get('DATABASE_URL') or \
        'sqlite:///'+os.path.join(basedir,'app.db')
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['2672813823@qq.com']
    POSTS_PER_PAGE = 3
    LANGUAGES = ['en','es', 'zh']
     # 【新增】从环境变量中读取百度翻译 API 的配置
    BAIDU_TRANSLATOR_APP_ID = os.environ.get('BAIDU_TRANSLATOR_APP_ID')
    BAIDU_TRANSLATOR_KEY = os.environ.get('BAIDU_TRANSLATOR_KEY')