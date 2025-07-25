from typing import Optional
import sqlalchemy as sa # 构建 SQL 表达式、定义数据库模式
import sqlalchemy.orm as so # 映射 Python 对象到数据库行、定义对象间关系
from app import db,login,app
from datetime import datetime,timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt


followers = sa.Table( # 只是一个关联表，并不是实体表，用于实现用户之间关注的桥梁（本质是User-User的多对多关系）
    'followers',
    db.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'), # 在 sa.Table 中定义列
              primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True)
)

class User(UserMixin,db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True) # so.Mapped[int]表明这个 Python 属性将被映射到一个数据库列，并且在 Python 中它的类型是 int
    #so.mapped_column，这是真正定义列映射的函数，在里面传入 sa 提供的类型和约束。
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    posts: so.WriteOnlyMapped['Post']=so.relationship(back_populates='author') # so.WriteOnlyMapped['Post']: 为“一对多”关系中的“多”的那一端提供的特殊映射类型，用于性能优化。
    # so.relationship(...): 它用来定义模型之间的关系，比如 User 和 Post 之间的一对多关系，或者 User 和 User 之间的多对多关系。
    # 它会在 Python 对象层面创建方便的导航属性（如 user.posts, post.author），并自动处理底层的 SQL JOIN 操作。

    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))
    
    following: so.WriteOnlyMapped['User'] = so.relationship(
        # secondary: 指定用于连接的“中间表”或“关联表”。
        # 在这里，我们使用在模型外部定义的 'followers' 表作为桥梁。
        secondary=followers, primaryjoin=(followers.c.follower_id == id), # primaryjoin是连接左侧用户到中间表，id指当前用户（关注发起者）
        secondaryjoin=(followers.c.followed_id == id), # secondaryjoin是连接中间表到右侧用户，id指目标用户（被关注者）
        back_populates='followers')# back_populates: 建立双向关系的关键。
        # 它告诉 SQLAlchemy，这个关系的“另一面”是 User 模型中名为 'followers' 的那个属性。
    
    followers: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following')

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def avatar(self, size): # 获取头像
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
    
    def follow(self, user): # 关注
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user): # 取关
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user): # 用于防止重复关注以及帮助实现取关逻辑
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None # 将查询结果转换为bool类型

    def followers_count(self): # 计算当前关注了多少用户
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery()) # 这是一个嵌套查询
        return db.session.scalar(query)

    def following_count(self): # 计算正在被多少用户关注
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery())
        return db.session.scalar(query)
    
    def following_posts(self): # 处理显示关注者帖子的逻辑
        Author = so.aliased(User) # 使用别名
        Follower = so.aliased(User)
        return ( # 连接所有帖子及其作者和关注作者的用户（注意是临时表）
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True) # 左外连接，显示右边没有数据的所有行
            .where(sa.or_( # 满足下面任一关系即可连接
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post) # 分组，去重（由于作者被多人关注，所以同一个帖子会重复）
            .order_by(Post.timestamp.desc()) # 排序
        )
    
    def get_reset_password_token(self, expires_in=600): # 为一个用户实例生成一个有时效性的密码重置令牌。
        return jwt.encode(
            # 将当前用户实例的 ID (self.id) 存入令牌。
            # 这是为了在验证令牌时能知道是哪个用户。
            {'reset_password': self.id, 'exp': time() + expires_in},# --- Payload (有效载荷) ---
            # 这是一个字典，包含了我们希望安全传递的信息。
            app.config['SECRET_KEY'], algorithm='HS256') # --- Secret Key (密钥) ---
            # 使用 Flask 应用配置中的 SECRET_KEY 来对 payload 进行加密签名。
            # 这是保证令牌不被篡改的核心
            # --- Algorithm (算法) ---
            # 指定使用 HS256 (HMAC using SHA-256) 签名算法，这是最常用的对称签名算法。
    
    @staticmethod
    def verify_reset_password_token(token): # 验证一个密码重置令牌的有效性。
        try:
             # --- 解码和验证 ---
            # jwt.decode() 会执行三个关键操作：
            # 1. 检查令牌的格式是否正确。
            # 2. 使用相同的 SECRET_KEY 和算法，验证令牌的签名是否未被篡改。
            # 3. 检查令牌中的 'exp' 字段，确认令牌是否已过期。
            # 如果以上任何一步失败，jwt.decode() 都会【抛出异常】。
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        # 如果令牌成功解码，并且我们获取到了用户 ID，
        # 就使用该 ID 从数据库中查询并返回对应的 User 对象。
        return db.session.get(User, id)

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))
    
class Post(db.Model):
    id:so.Mapped[int]=so.mapped_column(primary_key=True)
    body:so.Mapped[str]=so.mapped_column(sa.String(140))
    timestamp:so.Mapped[datetime]=so.mapped_column(index=True,default=lambda:datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))

    def __repr__(self):
        return '<Post {}>'.format(self.body)