# app/routes.py: 定义应用的URL路由和视图函数

# 1. 从 'app' 包中，导入那个名为 'app' 的 Flask 应用实例。
#    这个 'app' 实例是在 __init__.py 文件中创建的。
#    我们需要它来注册我们的路由。
from app import app
from flask import render_template,flash, redirect,url_for,request,g
from app.forms import LoginForm,RegistrationForm,EditProfileForm,EmptyForm,PostForm,ResetPasswordRequestForm,ResetPasswordForm
from flask_login import current_user, login_user
import sqlalchemy as sa
from app import db
from app.models import User,Post
from flask_login import logout_user,login_required
from urllib.parse import urlsplit
from datetime import timezone,datetime
from app.email import send_password_reset_email
from flask_babel import _, get_locale
from langdetect import detect,LangDetectException
from app.translate import translate


# 2. 定义一个视图函数 (View Function) - 'index'
#    这是一个普通的 Python 函数，它将处理用户的请求并返回一个响应。

# 3. 使用 '@app.route' 装饰器，将 URL 路径与下面的视图函数关联起来。
#    这意味着，当用户访问网站的根路径 ('/') 或 '/index' 路径时，
#    Flask 就会自动调用这个 'index' 函数。
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
   form = PostForm()
   if form.validate_on_submit():
        # 在确认提交文章后就会抓取文章所用语言
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user,language = language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('index'))
        # 任何改变了服务器状态的 POST 请求，都应该以一个到新页面的 redirect 作为响应，而不是直接返回 HTML。
        # 这可以彻底解决用户刷新页面时导致的重复提交问题，提供一个干净、可预测的用户体验。
   page = request.args.get('page', 1, type=int)
   posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
   # [值A] if [条件] else [值B]
   # 如果 [条件] 为 True，那么整个表达式的值就是 [值A]。
   # 否则（如果 [条件] 为 False），整个表达式的值就是 [值B]。
   # 如果 posts.has_next 为 True，这部分代码就会被执行，用来生成“下一页”的 URL。
   next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
   prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
   return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)

@app.route('/login', methods=['GET', 'POST'])
def login(): # 显示登录界面
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next') # 记住登录前上一个点击的路径，登录后可以直接定位
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout(): # 显示登出界面
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register(): # 显示注册界面
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!'))
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username): # 显示用户界面
    user = db.first_or_404(sa.select(User).where(User.username == username)) # 确保只需要查询一个
    page = request.args.get('page', 1, type=int) # 获取当前页码

    # 我们查询的是 user.posts，即当前页面所属用户的帖子，而不是 current_user.posts（当前登录用户）的帖子。
    # user.posts 是一个关系属性，它返回一个可查询对象。我们需要调用它的 .select() 方法来生成一个 SQLAlchemy 查询
    # 然后才能交给 db.session.scalars() 去执行。
    posts_query = user.posts.select().order_by(Post.timestamp.desc())
    # db.paginate() 的返回值不是一个简单的列表，而是一个功能非常丰富的 Pagination 对象
    posts = db.paginate(posts_query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'],
                        error_out=False)
    # user 视图函数需要一个 username 参数（因为它的路由是 @app.route('/user/<username>')）。
    # 我们把当前页面的用户 user 对象的用户名传给它，确保链接指向的还是同一个用户的个人资料页。
    # 假设当前用户是 susan，当前是第 2 页，那么这部分代码生成的 URL 就会是：/user/susan?page=3。
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    
    # 【关键步骤】准备表单数据：创建一个 EmptyForm 的实例
    #    即使这个表单是“空的”（没有可见的输入字段），
    #    我们也必须在后端创建一个它的 Python 对象实例。
    #    这个 'form' 对象包含了渲染自身所需的所有信息，
    #    特别是生成 CSRF 令牌的能力。
    form = EmptyForm()
    
    #  打包所有数据，传递给模板
    #    render_template 的作用就是渲染一个 HTML 文件，
    #    并把一个“上下文”字典传递给它。
    #    在这里，我们告诉 Jinja2 引擎：
    #    “在模板里，会有一个叫 'user' 的变量，它的值是 user 对象。”
    #    “会有一个叫 'posts' 的变量，它的值是 posts 列表。”
    #    “还会有一个叫 'form' 的变量，它的值是我们刚创建的 form 对象。”
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)
@app.before_request
def before_request(): # 显示用户上次浏览界面的时间
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    g.locale = str(get_locale())

@app.route('/edit_profile',methods=['GET','POST'])
@login_required
def edit_profile(): # 显示用户编辑界面
    # 1. 实例化表单时，传入当前用户的原始用户名。
    #    current_user 是 Flask-Login 提供的，代表当前已登录的用户。
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username): # 关注指定用户
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username): # 取关指定用户
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))
    
@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int) # 定位到page里面的内容，如果找不到，默认为1（第一页）
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template("index.html", title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url) # 与主页共享模板，根据有无传入form判断

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash(
            _('Check your email for the instructions to reset your password'))
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)

@app.route('/translate', methods=['POST'])
@login_required
def translate_text():
    # 3. 获取前端发送的数据
    #    - request.get_json(): 
    #      这是一个 Flask 提供的便捷函数。它会自动解析 HTTP 请求体 (Request Body) 中的数据，
    #      前提是前端发送请求时，设置了 'Content-Type': 'application/json' 请求头。
    #    - 它会将接收到的 JSON 字符串转换成一个 Python 字典。
    #    - data 变量现在的值会是：
    #      {
    #          'text': 'Hola, ¿cómo estás hoy?',
    #          'source_language': 'es',
    #          'dest_language': 'zh'
    #      }
    data = request.get_json()

    # 4. 调用后端翻译逻辑并返回结果
    #    - {'text': ... }: 
    #      我们正在创建一个 Python 字典。
    #    - translate(...): 
    #      调用我们之前在 app/translate.py 中定义的那个复杂的翻译函数。
    #      我们将从前端接收到的字典中的值，作为参数传递给它。
    #    - Flask 的一个强大特性：当你从一个视图函数返回一个 Python 字典时，
    #      Flask 会【自动】地将这个字典转换成一个 JSON 格式的响应，
    #      并设置正确的 'Content-Type': 'application/json' 响应头。
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['dest_language'])}