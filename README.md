# Microblog: 一个功能齐全的全栈微博客应用

本项目是基于 Miguel Grinberg 广受好评的 **[Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)** 教程的学习成果，并在此之上进行了**功能扩展与深度实践**。它完整地展示了如何使用 Python 和 Flask 从零开始，构建一个包含用户系统、高级社交功能、全文搜索、国际化和生产环境部署的现代 Web 应用。

![Microblog 网站截图](c:\Users\杨耀铭\Pictures\微信图片_20250911181530.png) 

## ✨ 核心功能列表

*   **全面的用户系统:**
    *   用户注册、登录与登出。
    *   安全的密码哈希存储与验证。
    *   基于 Flask-Login 的持久化会话管理（“记住我”）。
    *   通过电子邮件进行安全的密码重置。

*   **丰富的社交与互动功能:**
    *   **用户个人资料:**
        *   自定义个人简介。
        *   **自定义头像上传** (支持图片裁剪和缩放)，并优雅地回退到 Gravatar。
        *   实时追踪并显示用户“上次在线”时间。
    *   **社交网络:**
        *   用户**关注/取消关注**系统。
        *   主页动态流，只显示已关注用户的最新帖子。
    *   **互动系统:**
        *   用户可以在帖子下方**发表评论**。
        *   用户可以**删除**自己发表的帖子。
        *   **对话式私信系统:** 用户之间可以进行私密的一对一聊天，并带有**实时未读消息**通知。

*   **强大的内容管理:**
    *   用户可以发表、查看帖子。
    *   “发现”页面，浏览全站所有用户的公开帖子。
    *   高效的**分页**功能，流畅加载大量内容。
    *   基于 Elasticsearch 的高性能**全文搜索**。

*   **国际化与高级特性:**
    *   支持英语、西班牙语、中文等多语言界面 (i18n)。
    *   基于 Ajax 的**实时动态翻译**功能 (由百度翻译 API 驱动)。
    *   通过后台线程**异步发送电子邮件**，提升用户响应速度。
    *   通过 JavaScript 实现的用户信息**悬浮弹窗 (Popovers)**。

*   **专业的开发与部署实践:**
    *   采用**应用工厂模式**和**蓝图 (Blueprints)** 进行模块化架构设计。
    *   使用 Flask-Migrate (Alembic) 进行安全的数据库版本管理。
    *   通过自定义 CLI 命令 (`flask translate`) 简化开发工作流。
    *   覆盖核心功能的**单元测试**套件。
    *   完整的**生产环境部署**方案 (Linux + Nginx + Gunicorn + Supervisor)。

## 🛠️ 技术栈

*   **后端:** Python, **Flask**
*   **数据库:**
    *   开发: SQLite
    *   生产: **MySQL**
    *   ORM & 迁移: **Flask-SQLAlchemy**, **Flask-Migrate**
*   **表单处理:** Flask-WTF
*   **用户认证:** Flask-Login
*   **全文搜索:** **Elasticsearch** (通过 Docker 运行)
*   **图片处理:** **Pillow**
*   **国际化:** Flask-Babel
*   **邮件 & 异步:** Flask-Mail, Python `threading`
*   **前端:**
    *   模板引擎: Jinja2
    *   CSS 框架: **Bootstrap 5**
    *   JavaScript: 原生 JS (`fetch` API for Ajax), Moment.js (通过 Flask-Moment)
*   **部署与运维:**
    *   Web 服务器: **Nginx**
    *   WSGI 服务器: **Gunicorn**
    *   进程管理: **Supervisor**
    *   开发环境: **Docker**, **WSL 2**
*   **版本控制:** Git & GitHub

## 🚀 如何在本地运行

1.  **克隆仓库**
    ```bash
    git clone https://github.com/yangyaoming158/microblog.git
    cd microblog
    ```

2.  **创建并激活虚拟环境**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置环境变量**
    *   创建 `.env` 文件。
    *   在文件中设置必要的环境变量，如 `SECRET_KEY`, `DATABASE_URL` (如果使用 MySQL), `MAIL_...` 和 `BAIDU_...` API 密钥。
    *   `.flaskenv` 文件已包含 `FLASK_APP` 和 `FLASK_DEBUG` 的基本配置。

5.  **(可选) 启动 Elasticsearch**
    *   确保 Docker 正在运行，并在 `.env` 中设置 `ELASTICSEARCH_URL=http://localhost:9200`。
    *   运行 `docker run --rm -d ...` 命令启动 Elasticsearch 容器。

6.  **初始化数据库**
    ```bash
    flask db upgrade
    ```

7.  **编译翻译文件**
    ```bash
    flask translate compile
    ```

8.  **创建静态文件夹**
    *   确保 `app/static/avatars` 目录存在，以便存放上传的头像。
    ```bash
    mkdir -p app/static/avatars
    ```

9.  **运行应用**
    ```bash
    flask run
    ```
    应用将在 `http://localhost:5000` 上可用。

## 单元测试
要运行本项目的单元测试套件，请执行：
```bash
python tests.py
```