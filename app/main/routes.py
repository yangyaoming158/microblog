from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request, g, \
    current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
from langdetect import detect, LangDetectException
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm
from app.models import User, Post
from app.translate import translate
from app.main import bp
from app.main.forms import SearchForm


# g 对象： 是 Flask 提供的一个“请求全局”的存储空间
# 它就像一个“背包”，在一个完整的请求-响应周期内，你可以往里面放任何东西，并在该周期的任何地方（比如视图函数、模板）取出来用
# 请求结束后，背包里的东西会自动清空。
# @bp.before_app_request: 这是一个“钩子 (hook)”函数，它会在处理任何请求之前、在调用真正的视图函数之前被自动执行。
@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc) 
        db.session.commit()
        g.search_form = SearchForm()# 在每个请求开始时，都创建表单并放入背包
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
            if '-' in language:
                    # 【新增】规范化语言代码！
                    # 如果检测结果是 'zh-cn' 或 'zh-tw' 等，我们只取前面的 'zh'
                language = language.split('-')[0]
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user,
                    language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['dest_language'])}


# 为了实现可分享的 URL (/search?q=...)，搜索功能必须通过 GET 请求处理。
# 在后端，这意味着要从 request.args 获取数据，并使用 form.validate() 而不是 form.validate_on_submit()。
@bp.route('/search') # 1. 注册 /search 路由，只接受默认的 GET 请求
@login_required
def search():
    # 2. 【关键】验证 GET 表单
    #    - g.search_form 是我们在 before_request 处理器中创建的那个全局表单。
    #      因为它从 request.args 接收数据，所以它已经包含了 URL 中 '?q=...' 的值。
    #    - .validate() 只检查字段的验证器是否通过（比如 DataRequired，确保 q 不为空）。
    #      它不像 .validate_on_submit() 那样检查请求方法是否为 POST。
    if not g.search_form.validate():
        # 如果验证失败（用户提交了空表单），就重定向到 explore 页面。
        return redirect(url_for('main.explore'))
    
    # 3. 执行分页搜索
    #    从 URL 查询字符串中获取页码
    page = request.args.get('page', 1, type=int)
    # 调用我们之前在 SearchableMixin 中定义的 search 方法
    # - g.search_form.q.data: 获取用户在搜索框中输入的文本
    # - current_app.config['POSTS_PER_PAGE']: 获取每页显示的数量
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
                               
    # 4. 【关键】手动计算分页链接
    #    因为 Post.search() 返回的是一个普通列表和总数，而不是一个 Pagination 对象，
    #    所以我们需要自己计算“上一页”和“下一页”的 URL。
    
    # 计算下一页的 URL：
    # 如果【结果总数】大于【当前页码 * 每页数量】，说明还有下一页
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
        
    # 计算上一页的 URL：
    # 只要当前页码大于 1，就一定有上一页
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
        
    # 5. 渲染结果模板
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)

