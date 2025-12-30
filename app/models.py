from datetime import datetime, timezone
from hashlib import md5
from time import time
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask import current_app,url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt,json
from app import db, login
from app.search import add_to_index, remove_from_index, query_index

followers = sa.Table(
    'followers',
    db.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True)
)


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))

    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))

    # 【新增】添加一个字段，用于存储用户自定义头像的文件名
    # 它可以为 NULL，因为用户一开始没有自定义头像，会使用 Gravatar
    avatar_filename: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))

    posts: so.WriteOnlyMapped['Post'] = so.relationship(
        back_populates='author')
    following: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates='followers')
    followers: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following')
    
    # 一个用户发表的所有评论
    comments: so.WriteOnlyMapped['Comment'] = so.relationship(
        back_populates='author', lazy='dynamic', cascade='all, delete-orphan',passive_deletes=True)
    
    # 【新增字段】记录用户最后一次查看私信的时间
    # 这个字段可以为 NULL (用 Optional)，因为新用户还没有看过任何消息。
    last_message_read_time: so.Mapped[Optional[datetime]]
    # --- 【新增关系】 ---
    # `messages_sent`: 获取该用户作为【发送者】的所有消息
    messages_sent: so.WriteOnlyMapped['Message'] = so.relationship(
        # 同样，必须用 foreign_keys 来明确这个关系
        # 与 Message 模型中的 'author' 属性互为反向
        foreign_keys='Message.sender_id', back_populates='author')
    # `messages_received`: 获取该用户作为【接收者】的所有消息
    messages_received: so.WriteOnlyMapped['Message'] = so.relationship(
        # 与 Message 模型中的 'recipient' 属性互为反向
        foreign_keys='Message.recipient_id', back_populates='recipient')
    # 【新增关系】一个用户可以有多条通知
    notifications: so.WriteOnlyMapped['Notification'] = so.relationship(
        back_populates='user')

    
    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        # 【新增逻辑】如果用户有自定义头像，就使用它
        if self.avatar_filename:
            # 我们将把头像存在 static/avatars/ 目录下
            # url_for('static', ...) 会生成正确的 URL
            return url_for('static', filename=f'avatars/{self.avatar_filename}')
        else:
            digest = md5(self.email.lower().encode('utf-8')).hexdigest()
            return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
        

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery())
        return db.session.scalar(query)

    def following_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery())
        return db.session.scalar(query)

    def following_posts(self):
        Author = so.aliased(User)
        Follower = so.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(sa.or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return db.session.get(User, id)
    
    # 【新增方法】计算未读消息的数量
    def unread_message_count(self):
        # 获取用户上次读取消息的时间。如果是新用户 (值为 None)，
        # 就使用一个非常早的时间 (1900年) 作为起点。
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        # 构建查询：
        # 查找所有【接收者是我】(Message.recipient == self) 并且
        # 【消息时间戳晚于我上次读取时间】(Message.timestamp > last_read_time) 的消息。
        query = sa.select(Message).where(Message.recipient == self,
                                         Message.timestamp > last_read_time)
        # 在上面的查询基础上，只计算数量 (COUNT)，而不是获取消息本身，这样更高效。
        return db.session.scalar(sa.select(sa.func.count()).select_from(
            query.subquery()))
    
    # 【新增方法】添加或更新一条通知
    #  写入通知时调用
    def add_notification(self, name, data):
        # 先删除同名的旧通知，以实现“更新”的效果
        db.session.execute(self.notifications.delete().where(
            Notification.name == name))
        # 创建一条新通知
        # 将data中的纯数据转换为json形式
        # data不一定是数字
        # 例如将 1 转换为{"count": 1}
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class SearchableMixin(object):
    """
    一个可复用的混入类，为任何 SQLAlchemy 模型提供全文搜索的功能。
    任何希望被搜索的模型，只需要同时继承这个类即可。
    连接起数据库模型以及search.py（向Elasticsearch通话的渠道）
    例如: class Post(SearchableMixin, db.Model):

    自动化同步：SearchableMixin 与 SQLAlchemy 事件
    做什么： 创建一个 SearchableMixin 混入类，利用 SQLAlchemy 的事件监听机制 (before_commit, after_commit)，来自动地、在后台同步数据库和 Elasticsearch 索引。
    为什么： 避免了手动维护(少写很多)两个数据源的一致性。开发者的体验就像只在操作 SQL 数据库一样简单。
    工作流程：
    你在应用中执行 db.session.add(post) 和 db.session.commit()。
    before_commit 事件被触发，悄悄记下这个 post 对象。
    数据库提交成功后，after_commit 事件被触发，自动调用 add_to_index 函数，将这个 post 的数据也写入 Elasticsearch。
    学习要点： 掌握了如何使用 ORM 的高级事件系统来实现跨系统的数据自动同步。
    """

    # 1. --- 搜索方法 ---
    @classmethod
    def search(cls, expression, page, per_page):
        """
        为模型执行一次全文搜索。

        Args:
            cls: 调用此方法的模型类 (例如 Post)。
            expression (str): 用户的搜索查询字符串。
            page (int): 请求的页码。
            per_page (int): 每页的结果数量。

        Returns:
            tuple: (query_results, total_count)
                   - query_results: SQLAlchemy 查询结果对象。
                   - total_count: 匹配到的结果总数。
        """
        # a. 调用底层搜索函数，从 Elasticsearch 获取结果 ID 列表和总数
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        
        # b. 如果没有搜到任何结果，直接返回空列表，避免后续的数据库查询
        if total == 0:
            # 返回一个 SQLAlchemy 可接受的空结果格式
            return [], 0
            
        # c. 【关键】将 Elasticsearch 返回的 ID 列表，转换成一个能被 SQLAlchemy
        #          用来【保持排序】的结构。
        #    when 列表会是这样的：[(id_1, 0), (id_2, 1), (id_3, 2), ...]
        #    (id_1 是最相关的结果，所以它的排序值是 0)
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
            
        # d. 构建一个 SQLAlchemy 查询，一次性地从数据库中获取所有匹配的对象
        #    - sa.select(cls): 查询这个模型 (如 Post)。
        #    - .where(cls.id.in_(ids)): 只查询那些 ID 在 Elasticsearch 返回的列表中的对象。
        #    - .order_by(db.case(...)):
        #      - db.case() 是一个 SQL CASE 语句，是保持排序的“魔法”所在。
        #      - 它会生成类似 "ORDER BY CASE WHEN id=id_1 THEN 0 WHEN id=id_2 THEN 1 ... END" 的 SQL。
        #      - 这确保了从数据库返回的对象列表，其【顺序】与 Elasticsearch 返回的【相关度顺序】完全一致。
        query = sa.select(cls).where(cls.id.in_(ids)).order_by(
            db.case(*when, value=cls.id))
            
        # e. 执行查询并返回结果
        return db.session.scalars(query), total

    # 2. --- 自动索引同步 (通过 SQLAlchemy 事件) ---
    @classmethod
    def before_commit(cls, session):
        """
        在数据库事务【提交之前】被自动调用的事件处理器。
        """
        # 在 session 对象上创建一个临时的 `_changes` 字典。
        # `session.new`, `session.dirty`, `session.deleted` 是 SQLAlchemy 的内置属性，
        # 它们分别包含了本次事务中所有【新增的】、【被修改的】和【被删除的】对象。
        # 我们把这些对象暂存起来，因为在 commit 之后，这些信息就丢失了。
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        """
        在数据库事务【成功提交之后】被自动调用的事件处理器。
        """
        # 遍历所有【新增的】和【被修改的】对象
        # （注意，教程中分开了两个 for 循环，这里可以合并以简化）
        for obj in session._changes['add'] + session._changes['update']:
            # 检查这个对象是否是 SearchableMixin 的一个实例 (即，是否是可搜索的模型)
            if isinstance(obj, SearchableMixin):
                # 如果是，就调用 add_to_index 将其添加到 Elasticsearch
                add_to_index(obj.__tablename__, obj)
        
        # 遍历所有【被删除的】对象
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                # 如果是，就调用 remove_from_index 将其从 Elasticsearch 中移除
                remove_from_index(obj.__tablename__, obj)
                
        # 清理临时变量
        session._changes = None

    # 3. --- 手动重建索引的方法 ---
    @classmethod
    def reindex(cls):
        """
        手动为整个模型的所有数据重建 Elasticsearch 索引。
        这在第一次集成搜索功能，或者索引损坏时非常有用。
        """
        # 遍历数据库中该模型的所有对象
        for obj in db.session.scalars(sa.select(cls)):
            # 逐一将它们添加到索引中
            add_to_index(cls.__tablename__, obj)

# 4. --- 将事件处理器【注册】到 SQLAlchemy 的会话事件系统中 ---

# 监听 db.session 的 'before_commit' 事件，当事件发生时，调用 SearchableMixin.before_commit 方法
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)

# 监听 db.session 的 'after_commit' 事件，当事件发生时，调用 SearchableMixin.after_commit 方法
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class Post(SearchableMixin,db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    # 一篇帖子下的所有评论
    comments: so.WriteOnlyMapped['Comment'] = so.relationship(
        back_populates='post', lazy='dynamic', cascade='all, delete-orphan',passive_deletes=True)
    # 【新增】标题字段
    # 设置 default='' 确保旧帖子在迁移时不会报错，nullable=False 强制要求有标题（哪怕是空的）
    title: so.Mapped[str] = so.mapped_column(sa.String(100), default='', nullable=False)

    __searchable__ = ['body']


    def __repr__(self):
        return '<Post {}>'.format(self.body)
    
    # 【新增】一个封装了删除逻辑的类方法
    @classmethod
    def delete_post_with_dependencies(cls, post_id):
        post = db.get_or_404(cls, post_id)
        
        # 删除所有关联的评论
        comments_query = sa.select(Comment).where(Comment.post_id == post.id)
        comments = db.session.scalars(comments_query).all()
        for comment in comments:
            db.session.delete(comment)
            
        # 删除帖子本身
        db.session.delete(post)
        
        # 注意：commit 留给调用者来做


class Comment(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    # --- 关系 ---
    # 评论的作者
    author_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), 
                                                 index=True)
    author: so.Mapped['User'] = so.relationship('User', back_populates='comments')
    
    # 这条评论是属于哪篇帖子的
    post_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('post.id', ondelete='CASCADE'),
                                               index=True)
    post: so.Mapped['Post'] = so.relationship('Post', back_populates='comments')

    def __repr__(self):
        return f'<Comment {self.body}>'


class Message(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    # --- 核心外键 ---
    # 发送者的用户 ID，外键指向 user 表的 id
    sender_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                                 index=True)
    # 接收者的用户 ID，同样是外键指向 user 表的 id
    recipient_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                                    index=True)
    # 私信的正文内容
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    # 私信的发送时间戳，默认值为当前的 UTC 时间
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))

    # --- 反向关系 (Back-Populates) ---
    # `author` 关系：通过 sender_id 链接回 User 模型
    author: so.Mapped[User] = so.relationship(
        # 【关键】当一个模型有多个外键指向同一个模型时，
        # 必须使用 foreign_keys 来明确指出这个关系应该使用哪个外键
        foreign_keys='Message.sender_id',
        # 这个关系与 User 模型中的 'messages_sent' 属性互为反向
        back_populates='messages_sent')
    # `recipient` 关系：通过 recipient_id 链接回 User 模型
    recipient: so.Mapped[User] = so.relationship(
        foreign_keys='Message.recipient_id',
        back_populates='messages_received')

    def __repr__(self):
        return '<Message {}>'.format(self.body)


class Notification(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    # 通知的名称，如 'unread_message_count'
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    # 通知属于哪个用户
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)
    timestamp: so.Mapped[float] = so.mapped_column(index=True, default=time)
    # 存储具体数据的 JSON 字符串
    payload_json: so.Mapped[str] = so.mapped_column(sa.Text)

    user: so.Mapped[User] = so.relationship(back_populates='notifications')

    # 读取通知时调用
    def get_data(self):
        # 将 JSON 字符串解析回 Python 对象
        return json.loads(str(self.payload_json))
        # json.loads(json_string): 接收一个 JSON 格式的字符串
        # 并把它反序列化 (deserialize) 成一个等价的 Python 对象。
        # 字典、列表、数字、字符串等
        # 当初存进去什么，就还原成什么
        