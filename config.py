import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def _env_list(name, default=''):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'app.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUPPRESS_SEND = False

    ADMINS = _env_list('ADMINS', '2672813823@qq.com')
    POSTS_PER_PAGE = int(os.environ.get('POSTS_PER_PAGE') or 10)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH') or 2 * 1024 * 1024)
    LANGUAGES = ['en', 'es', 'zh']

    BAIDU_TRANSLATOR_APP_ID = os.environ.get('BAIDU_TRANSLATOR_APP_ID')
    BAIDU_TRANSLATOR_KEY = os.environ.get('BAIDU_TRANSLATOR_KEY')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    AVATAR_UPLOAD_DIR = (
        os.environ.get('AVATAR_UPLOAD_DIR') or
        os.path.join(basedir, 'app', 'static', 'avatars')
    )

    @classmethod
    def validate(cls):
        pass


class DevConfig(Config):
    DEBUG = True
    SECRET_KEY = Config.SECRET_KEY or 'you-will-never-guess'


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False
    ELASTICSEARCH_URL = None
    MAIL_SUPPRESS_SEND = True
    BAIDU_TRANSLATOR_APP_ID = None
    BAIDU_TRANSLATOR_KEY = None
    POSTS_PER_PAGE = 10


class ProductionConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY')

    @classmethod
    def validate(cls):
        secret_key = cls.SECRET_KEY or os.environ.get('SECRET_KEY')
        if not secret_key:
            raise RuntimeError('SECRET_KEY must be set when FLASK_CONFIG=production')
        cls.SECRET_KEY = secret_key


CONFIG_BY_NAME = {
    'development': DevConfig,
    'dev': DevConfig,
    'testing': TestConfig,
    'test': TestConfig,
    'production': ProductionConfig,
    'prod': ProductionConfig,
    'default': DevConfig,
}


def get_config_class(name=None):
    config_name = (name or os.environ.get('FLASK_CONFIG') or 'default').lower()
    return CONFIG_BY_NAME.get(config_name, DevConfig)
