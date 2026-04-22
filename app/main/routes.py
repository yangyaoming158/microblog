from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request, g, \
    current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
from langdetect import detect, LangDetectException
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm,MessageForm,ChangeAvatarForm
from app.models import User, Post,Comment,Message,Notification
from app.translate import translate
from app.main import bp
from app.main.forms import SearchForm,CommentForm
import os
from werkzeug.utils import secure_filename
from PIL import Image

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
    empty_form = EmptyForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
            if '-' in language:
                    # 【新增】规范化语言代码！
                    # 如果检测结果是 'zh-cn' 或 'zh-tw' 等，我们只取前面的 'zh'
                language = language.split('-')[0]
        except LangDetectException:
            language = ''
        post = Post(title=form.title.data,  # 【新增】保存标题
                    body=form.post.data, 
                    author=current_user,
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
    hero_stats = {
        'post_count': db.session.scalar(sa.select(sa.func.count()).select_from(current_user.posts.select().subquery())),
        'following_count': current_user.following_count(),
        'followers_count': current_user.followers_count(),
        'unread_message_count': current_user.unread_message_count()
    }
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, empty_form=empty_form,
                           hero_stats=hero_stats)


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
    hero_stats = {
        'post_count': db.session.scalar(sa.select(sa.func.count()).select_from(current_user.posts.select().subquery())),
        'following_count': current_user.following_count(),
        'followers_count': current_user.followers_count(),
        'unread_message_count': current_user.unread_message_count()
    }
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, hero_stats=hero_stats)


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
    empty_form = EmptyForm() # 使用空模板来实现删除帖子按钮
    # avatar_form 用于“更换头像”
    # 我们只在用户查看自己主页时才需要它，但为了简化，每次都创建也无妨
    avatar_form = ChangeAvatarForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form,empty_form=empty_form,avatar_form=avatar_form)


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


@bp.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    # 1. 根据传入的 post_id，从数据库中查询要删除的帖子。
    #    使用 db.get_or_404() 是一个非常好的实践，如果找不到帖子，
    #    它会自动返回一个 404 Not Found 错误页面。
    post = db.get_or_404(Post, post_id)

    # 2. 【核心安全检查】验证当前登录的用户是否是这篇帖子的作者。
    #    这可以防止一个用户通过构造 URL 来删除别人的帖子！
    if post.author != current_user:
        # 如果不是作者，可以使用 abort() 来立即返回一个错误。
        # 403 Forbidden 表示“禁止访问”。
        from flask import abort
        abort(403)

       # 【调用封装好的方法】
    Post.delete_post_with_dependencies(post_id)
    
    db.session.commit() # 在视图层面统一提交
    # 4. 给出反馈，并重定向
    flash(_('Your post has been deleted!'))
    
    # 将用户重定向回他/她自己的个人资料页面
    return redirect(url_for('main.user', username=current_user.username))



@bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def post(post_id):
    # 1. 根据 ID 查询帖子，如果找不到则返回 404
    post = db.get_or_404(Post, post_id)
    
    # 2. 创建一个用于发表新评论的表单
    form = CommentForm()
    
    # 3. 处理表单提交 (POST 请求)
    if form.validate_on_submit():
        # 创建一个新的 Comment 对象
        comment = Comment(
            
            body=form.body.data,
            author=current_user,
            post=post, # 直接将 post 对象关联起来
        )
        db.session.add(comment)
        db.session.commit()
        flash(_('Your comment has been published.'))
        
        # 使用 Post/Redirect/Get 模式，重定向回同一个页面以避免重复提交
        # url_for('main.post', ...) 会生成 /post/<post_id> 这样的 URL
        return redirect(url_for('main.post', post_id=post.id))
    
    # 4. 获取并分页显示这篇帖子的所有评论 (GET 请求时)
    page = request.args.get('page', 1, type=int)
    # post.comments 是一个可查询对象，我们可以直接对其进行排序和分页
    comments = db.paginate(
        post.comments.select().order_by(Comment.timestamp.asc()),
        page=page, per_page=10, error_out=False)
        
    # 5. 计算分页链接
    next_url = url_for('main.post', post_id=post.id, page=comments.next_num) \
        if comments.has_next else None
    prev_url = url_for('main.post', post_id=post.id, page=comments.prev_num) \
        if comments.has_prev else None
    
    # 【新增步骤 1】实例化 EmptyForm
    # 这个表单用于侧边栏的 关注/取消关注 按钮 (以及之前的删除按钮)
    empty_form = EmptyForm()

    return render_template('post_detail.html', title=post.body, post=post,
                           comments=comments.items, form=form,
                           next_url=next_url, prev_url=prev_url,
                           
                           # 【新增步骤 2】将 empty_form 传递给模板
                           empty_form=empty_form)

#根据给定的 username，获取 user 对象
#然后把它“填充”到一个专门为弹窗设计的、小巧的 HTML 模板中，并把最终生成的 HTML 片段作为响应返回
@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)



@bp.route('/messages')
@login_required
def messages():
    page = request.args.get('page', 1, type=int)
    # 【核心重构】查询所有与我对话过的用户，并按最近消息时间排序
    # 我们需要一个更复杂的查询来获取每个对话的最后一条消息
    # 为了简化，我们先获取所有对话伙伴，后续可以优化
    sent_to_q = db.select(Message.recipient_id).where(Message.sender_id == current_user.id)
    received_from_q = db.select(Message.sender_id).where(Message.recipient_id == current_user.id)
    # 获取所有与我相关的用户ID，并去重
    user_ids = list(set(db.session.scalars(sent_to_q).all() + db.session.scalars(received_from_q).all()))
    if not user_ids:
        # 如果没有对话伙伴，直接返回一个空的分页对象或者空列表
        # 这里我们手动模拟一个空的分页结果，或者直接渲染模板并传入空列表
        # 最简单的做法是直接传空列表给模板，让模板显示“暂无消息”
        return render_template('messages.html', users=[], next_url=None, prev_url=None)
        
    else:
        # 查询这些用户，未来可以按最后消息时间排序
        users_query = sa.select(User).where(User.id.in_(user_ids))
        # 使用 paginate 来分页显示这些“对话伙伴”
        pagination = db.paginate(users_query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
        users = pagination.items
        
    next_url = url_for('main.messages', page=pagination.next_num) \
        if pagination.has_next else None
    prev_url = url_for('main.messages', page=pagination.prev_num) \
        if pagination.has_prev else None
    return render_template('messages.html', users=users,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    # 获取 'since' 参数，如果不存在则默认为 0.0
    since = request.args.get('since', 0.0, type=float)
    # 查询比 'since' 时间戳更新的所有通知
    query = current_user.notifications.select().where(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    notifications = db.session.scalars(query)
    # 将结果格式化为 JSON 列表并返回
    return [{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications]


@bp.route('/conversation/<username>', methods=['GET', 'POST'])
@login_required
def conversation(username):
    # 找到对话的另一方
    user = db.first_or_404(sa.select(User).where(User.username == username))
    
    # 创建用于发送新消息的表单
    form = MessageForm() 
    
    if form.validate_on_submit():
        
        # 处理发送新消息的逻辑
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        # 给对方发送通知
        user.add_notification('unread_message_count', user.unread_message_count())
        db.session.commit()
        flash(_('Your message has been sent.'))
        # 提交后重定向到同一页面，刷新聊天记录
        return redirect(url_for('main.conversation', username=username))
    
    # 访问此页面时，将与该用户的所有消息标记为已读
    current_user.last_message_read_time = datetime.now(timezone.utc)
    # 并且将未读消息通知清零
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    
    # 【核心】查询你和这个 user 之间的所有消息
    page = request.args.get('page', 1, type=int)
    messages_query = sa.select(Message).where(
        sa.or_(
            sa.and_(Message.recipient_id == current_user.id, Message.sender_id == user.id),
            sa.and_(Message.recipient_id == user.id, Message.sender_id == current_user.id)
        )
    ).order_by(Message.timestamp.desc()) # 按时间【降序】，最新的消息在最上面
    
    messages = db.paginate(messages_query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)

    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    
    return render_template('conversation.html', title=f"Conversation with {username}",
                           form=form, recipient=user, messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


# 换头像
@bp.route('/change_avatar', methods=['GET', 'POST'])
@login_required
def change_avatar():
    form = ChangeAvatarForm()
    if form.validate_on_submit():
        if form.avatar.data:
            # 这里的逻辑和之前 edit_profile 里的完全一样
            random_hex = os.urandom(8).hex()
            f_name, f_ext = os.path.splitext(form.avatar.data.filename)
            avatar_fn = random_hex + f_ext
            avatar_path = os.path.join(current_app.root_path, 'static/avatars', avatar_fn)
            
            # (可选) 删除旧头像文件以节省空间
            if current_user.avatar_filename:
                old_avatar_path = os.path.join(current_app.root_path, 'static/avatars', current_user.avatar_filename)
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)
            
            output_size = (128, 128)
            i = Image.open(form.avatar.data)
            i.thumbnail(output_size)
            i.save(avatar_path)
            
            current_user.avatar_filename = avatar_fn
            db.session.commit()
            flash(_('Your avatar has been updated!'))
            # 上传成功后，重定向回用户主页
            return redirect(url_for('main.user', username=current_user.username))
    
    # 如果是 GET 请求，也重定向回用户主页，因为我们不在一个单独的页面上显示这个表单
    return redirect(url_for('main.user', username=current_user.username))