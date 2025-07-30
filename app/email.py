# 导入 Thread 类，用于创建和管理后台线程
from threading import Thread
# 导入 current_app 代理，用于在请求上下文中安全地访问当前的 Flask 应用实例
from flask import current_app
# 导入 Message 类，用于构建邮件对象
from flask_mail import Message
# 导入在 app/__init__.py 中创建的 mail 实例 (Flask-Mail 扩展)
from app import mail


def send_async_email(app, msg):
    """
    这是一个在【后台线程】中运行的函数，负责实际的邮件发送。

    Args:
        app: 【真实】的 Flask 应用实例。不能是 current_app 代理。
        msg: 已经构建好的 Message 邮件对象。
    """
    # 【关键】手动创建一个应用上下文 (Application Context)。
    # 因为这个函数在一个全新的线程中运行，它脱离了 Flask 的主请求处理流程，
    # 所以像 url_for() 这样的函数或者 Flask 扩展 (如 Flask-Mail) 在工作时，
    # 无法自动找到它们需要的应用配置。
    # `with app.app_context():` 手动创建了一个这样的环境，
    # 使得在这个代码块内部，所有 Flask 的功能都能正常访问到 'app' 实例的配置。
    with app.app_context():
        # 在应用上下文中，调用 mail.send() 方法来发送邮件。
        # 这是一个耗时的网络 I/O 操作，现在它在后台进行，不会阻塞主线程。
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    """
    这是应用中其他部分应该调用的【主】邮件发送函数。
    它负责构建邮件对象，并启动一个后台线程来发送它。

    Args:
        subject (str): 邮件主题。
        sender (str): 发件人邮箱地址。
        recipients (list[str]): 收件人邮箱地址列表。
        text_body (str): 纯文本格式的邮件正文。
        html_body (str): HTML 格式的邮件正文。
    """
    # 1. 创建一个 Message 对象，填充邮件的基本信息。
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    
    # 2. 创建并启动一个新的后台线程。
    #    - Thread(): 创建一个线程对象。
    #    - target=send_async_email: 告诉这个新线程要去执行的目标函数是 send_async_email。
    #    - args=(...): 这是一个元组，包含了要传递给目标函数的参数。
    #    - 【关键】current_app._get_current_object():
    #      - current_app 是一个“代理”对象，它只在处理当前请求的这个线程中有效。
    #        我们不能直接把这个“代理”传递给新线程，因为在新线程中它会失效。
    #      - ._get_current_object() 是一个特殊的方法，用于从代理对象中
    #        【提取出背后真实、具体】的 Flask 应用实例对象。
    #      - 我们把这个【真实】的 app 对象和 msg 对象一起作为参数传递给后台线程。
    #    - .start(): 立即启动这个后台线程，主线程（即处理 Web 请求的线程）会继续向下执行，
    #      而不会等待邮件发送完成。
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start()