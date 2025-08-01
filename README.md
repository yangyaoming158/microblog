# Microblog: 一个功能齐全的全栈微博客应用

本项目是基于 Miguel Grinberg 广受好评的 **[Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)** 教程，并在此基础上进行了功能扩展和个性化实践的学习成果。它展示了如何使用 Python 和 Flask 从零开始，构建一个包含用户系统、社交功能、全文搜索、国际化和后台任务等特性的现代 Web 应用。

![Microblog 网站截图](https://your-image-hosting.com/screenshot.png) 
*(提示：你可以截一张你网站的最终效果图，上传到一个图床，然后在这里替换链接)*

## ✨ 核心功能列表

*   **用户认证系统:**
    *   用户注册、登录与登出
    *   安全的密码哈希存储
    *   基于 Flask-Login 的会话管理
    *   通过电子邮件进行密码重置
*   **社交与互动:**
    *   用户个人资料页面，支持自定义简介和头像 (Gravatar)
    *   用户关注/取消关注系统
    *   **帖子评论功能**：用户可以在帖子下方发表评论
    *   **帖子删除功能**：用户可以删除自己发表的帖子
*   **内容管理:**
    *   用户可以发表、查看帖子
    *   主页动态流，显示已关注用户的最新帖子
    *   “发现”页面，浏览全站所有用户的帖子
    *   高效的分页功能，流畅加载大量内容
*   **高级功能:**
    *   **全文搜索:** 基于 Elasticsearch 的高性能站内帖子搜索
    *   **国际化 (i18n):** 支持英语、西班牙语和中文等多语言界面
    *   **实时翻译:** 通过后台 Ajax 请求，调用第三方 API (百度翻译) 实时翻译帖子内容
    *   **后台任务:** 使用后台线程异步发送电子邮件，提升用户响应速度
*   **开发与部署:**
    *   使用 Flask-Migrate (Alembic) 进行数据库版本管理
    *   通过自定义 CLI 命令 (`flask translate`) 简化开发工作流
    *   完善的单元测试套件
    *   已在生产环境（Linux + Nginx + Gunicorn + Supervisor）成功部署

## 🛠️ 技术栈

*   **后端:** Python, **Flask**
*   **数据库:**
    *   开发: SQLite
    *   生产: **MySQL**
    *   ORM & 迁移: **Flask-SQLAlchemy**, **Flask-Migrate**
*   **表单处理:** Flask-WTF
*   **用户认证:** Flask-Login
*   **全文搜索:** **Elasticsearch** (通过 Docker 运行)
*   **国际化:** Flask-Babel
*   **异步任务:** Python `threading`
*   **邮件:** Flask-Mail
*   **前端:**
    *   模板引擎: Jinja2
    *   CSS 框架: **Bootstrap 5**
    *   JavaScript: 原生 JS (`fetch` API for Ajax), Moment.js (通过 Flask-Moment)
*   **部署:**
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
    *   创建一个 `.env` 文件。
    *   在文件中设置必要的环境变量，至少需要 `SECRET_KEY`。为了使用所有功能，还需要配置 `MAIL_...` 和翻译服务的 API 密钥。
    *   `.flaskenv` 文件已包含 `FLASK_APP` 和 `FLASK_DEBUG` 的基本配置。

5.  **(可选) 启动 Elasticsearch**
    *   确保 Docker 正在运行。
    *   运行以下命令来启动 Elasticsearch 服务：
        ```bash
        docker run --name elasticsearch -d --rm -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" docker.elastic.co/elasticsearch/elasticsearch:8.14.0
        ```
    *   并在 `.env` 文件中设置 `ELASTICSEARCH_URL=http://localhost:9200`。

6.  **初始化数据库**
    ```bash
    flask db upgrade
    ```

7.  **编译翻译文件**
    ```bash
    flask translate compile
    ```

8.  **运行应用**
    ```bash
    flask run
    ```
    应用将在 `http://localhost:5000` 上可用。

## 单元测试
要运行本项目的单元测试套件，请执行：
```bash
python tests.py
```