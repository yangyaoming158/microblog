from app import cli
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import app, db
from app.models import User, Post

@app.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'so': so, 'db': db, 'User': User, 'Post': Post}
# microblog.py: 应用程序的主入口点

# 从我们自己创建的 'app' 包中，导入那个名为 'app' 的 Flask 应用实例。
# 这里的第一个 'app' 是指 'app/' 这个文件夹（Python 包）。
# 第二个 'app' 是指在 app/__init__.py 中创建的那个 Flask 对象。