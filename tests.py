#!/usr/bin/env python
from datetime import datetime, timezone, timedelta
import unittest
from app import create_app, db # 导入应用工厂函数和 db 实例
from app.models import User, Post
from config import Config


# 应用上下文 (app_context) 的深入解释：
# current_app 的秘密： current_app 并不是 app 本身，它是一个“聪明的指针”。它会在当前线程里寻找一个被“激活”的应用上下文，然后把自己指向那个上下文里的 app 实例。
# 为什么 setUp 中需要 self.app_context.push()?
# db.create_all() 这个函数在内部需要知道数据库在哪里，所以它需要访问 current_app.config['SQLALCHEMY_DATABASE_URI']。
# 但是，在 setUp 这个函数里，我们只是创建了 self.app，还没有一个真实的 Web 请求。所以 current_app 这个“指针”是“悬空”的，不知道该指向谁。
# self.app_context.push() 这个动作，就是手动地告诉 current_app：“嘿，现在请你指向 self.app 这个实例！”
# 这样，db.create_all() 就能通过 current_app 成功地找到配置，并连接到正确的（内存）数据库了。


# 1. 创建一个【专用于测试】的配置类
#    - 它继承自生产环境的 Config 类，这样可以继承所有通用的配置。
#    - 然后，它会【覆盖】掉那些在测试中需要特别设置的选项。
class TestConfig(Config):
    # a. 开启测试模式
    #    - TESTING = True 是 Flask 的一个内置配置。
    #    - 当它为 True 时，Flask 会禁用一些功能（如错误邮件通知），
    #      并启用一些便于测试的特性，让异常更容易被捕获。
    TESTING = True
    
    # b. 覆盖数据库 URI
    #    - 将数据库连接字符串强制设置为 'sqlite://'。
    #    - 这告诉 SQLAlchemy 使用一个【纯内存中】的 SQLite 数据库，
    #      而不是开发时使用的、基于磁盘的 'app.db' 文件。
    #    - 优点：速度快、自动清理、与开发数据库完全隔离。
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


# 2. 定义一个测试用例类，继承自 unittest.TestCase
class UserModelCase(unittest.TestCase):
    
    # 3. setUp() 方法：在【每一个】测试方法运行【之前】自动执行
    #    - 它的作用是为每个测试创建一个全新的、干净的、隔离的运行环境。
    def setUp(self):
        # a. 创建一个全新的应用实例
        #    - 调用应用工厂函数 create_app()，并明确传入我们上面定义的 TestConfig。
        #    - self.app 存储了这个为本次测试专属创建的 Flask 应用实例。
        self.app = create_app(TestConfig)
        
        # b. 创建并推送一个应用上下文
        #    - self.app.app_context() 从应用实例中创建一个应用上下文对象。
        #    - self.app_context.push() 【激活】这个上下文。
        #    - 这一步至关重要，它使得像 db (Flask-SQLAlchemy) 这样的扩展，
        #      能够通过 current_app 代理找到应用的配置（比如那个内存数据库的 URI）。
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # c. 创建数据库表
        #    - db.create_all() 会在我们刚刚配置的内存数据库中，创建所有
        #      在 models.py 中定义的表 (User, Post 等)。
        #    - 这确保了每个测试开始时，都有一个干净、完整的数据库结构。
        db.create_all()

    # 4. tearDown() 方法：在【每一个】测试方法运行【之后】自动执行 (无论成功或失败)
    #    - 它的作用是彻底清理本次测试所使用的所有资源，防止对后续测试产生影响。
    def tearDown(self):
        # a. 移除数据库会话
        #    - 确保所有数据库连接都被正确关闭。
        db.session.remove()
        
        # b. 删除所有数据库表
        #    - db.drop_all() 会删除内存数据库中的所有表。
        #    - 这确保了下一个测试的 setUp() 将会从一个完全空的数据库开始。
        db.drop_all()
        
        # c. 弹出应用上下文
        #    - self.app_context.pop() 【撤销】之前推送的上下文，
        #      将环境恢复到测试开始前的状态。
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='susan', email='susan@example.com')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                         'd4c74594d841139328695756648b6bd6'
                                         '?d=identicon&s=128'))

    def test_follow(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        following = db.session.scalars(u1.following.select()).all()
        followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(following, [])
        self.assertEqual(followers, [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.following_count(), 1)
        self.assertEqual(u2.followers_count(), 1)
        u1_following = db.session.scalars(u1.following.select()).all()
        u2_followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(u1_following[0].username, 'susan')
        self.assertEqual(u2_followers[0].username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.following_count(), 0)
        self.assertEqual(u2.followers_count(), 0)

    def test_follow_posts(self):
        # create four users
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        db.session.add_all([u1, u2, u3, u4])

        # create four posts
        now = datetime.now(timezone.utc)
        p1 = Post(body="post from john", author=u1,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(body="post from susan", author=u2,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(body="post from mary", author=u3,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(body="post from david", author=u4,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        # check the following posts of each user
        f1 = db.session.scalars(u1.following_posts()).all()
        f2 = db.session.scalars(u2.following_posts()).all()
        f3 = db.session.scalars(u3.following_posts()).all()
        f4 = db.session.scalars(u4.following_posts()).all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])


if __name__ == '__main__':
    unittest.main(verbosity=2)