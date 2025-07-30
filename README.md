# Microblog - 基于 Flask 的全功能微博客应用

本项目是跟随 Miguel Grinberg 广受好评的 **[Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)** 教程，在一个现代化的 **WSL 2 (Windows Subsystem for Linux)** 开发环境中，从零开始构建的全功能 Web 应用。

这个仓库不仅是教程的学习成果，更是一个展示如何在 Windows 上利用 WSL 2 和 Docker 搭建专业、高效的全栈开发环境的范例。

## 分支说明

*   `master` / `main`: 可能包含项目的早期版本或一个稳定的基础版本。
*   **`chapter-wsl-version`** (或你命名的分支): **包含了截至教程第十六章的全部功能**，并采用了**应用工厂模式 (Application Factory)** 和**蓝图 (Blueprints)** 进行了全面的架构重构。

## 核心功能列表

*   **用户系统:** 注册、登录/登出、密码哈希存储、密码重置 (通过邮件)。
*   **个人中心:** 可编辑的个人资料、个人简介、动态头像 (Gravatar)、上次在线时间。
*   **社交功能:** 用户之间的“关注”与“取消关注”功能。
*   **动态流 (Feeds):**
    *   **首页:** 显示用户自己及所关注用户的帖子时间线。
    *   **发现页:** 显示全站所有用户的公开帖子。
*   **内容管理:**
    *   发布新帖子。
    *   所有帖子列表均支持**分页**。
*   **全文搜索:**
    *   集成 **Elasticsearch** (通过 Docker 运行)，提供强大的站内帖子搜索功能。
    *   搜索结果按相关度排序并支持分页。
*   **国际化 (i18n & l10n):**
    *   支持多语言界面 (英语, 西班牙语, 中文)。
    *   通过 **Flask-Babel** 自动根据用户浏览器语言进行切换。
*   **实时翻译:**
    *   通过 **Ajax** 和**第三方翻译 API** (本项目使用百度翻译) 实现帖子的实时、动态翻译，无需刷新页面。
    *   自动检测帖子源语言。
*   **后台任务与通知:**
    *   通过后台线程异步发送电子邮件。
    *   配置了生产环境下的错误日志记录与邮件通知。

## 架构亮点

本项目采用了现代 Flask 应用开发的最佳实践：

*   **应用工厂模式:** 使用 `create_app()` 函数动态创建应用实例，彻底解决了循环导入问题，并实现了完美的测试环境隔离。
*   **蓝图 (Blueprints):** 将应用按功能 (`main`, `auth`, `errors`) 拆分成独立的、高内聚的模块，使得代码结构清晰、易于维护和复用。
*   **抽象层设计:** 搜索和翻译等外部服务被封装在独立的模块中，与主应用逻辑解耦，便于未来替换或扩展。
*   **自动化索引:** 利用 SQLAlchemy 的事件监听机制，实现了数据库与 Elasticsearch 索引之间的自动同步。

## 技术栈

*   **开发环境:** Windows 11 + **WSL 2 (Ubuntu)**
*   **后端:** Python 3, Flask
*   **数据库:** Flask-SQLAlchemy (ORM), SQLite (开发), Flask-Migrate (迁移)
*   **表单 & 认证:** Flask-WTF, Flask-Login
*   **国际化 & 时间:** Flask-Babel, Flask-Moment
*   **邮件 & 命令行:** Flask-Mail, Click
*   **全文搜索:** **Elasticsearch**
*   **容器化:** **Docker Desktop (for Windows)**
*   **前端:** HTML5, Bootstrap 5, Jinja2, JavaScript (Ajax/Fetch API)

## 如何在本地运行 (WSL 2 环境)

1.  **前置条件:**
    *   Windows 10/11 已安装并启用 WSL 2。
    *   已从 Microsoft Store 安装 Ubuntu 发行版。
    *   已安装并运行 Docker Desktop，并确保在 `Settings > Resources > WSL Integration` 中开启了对 Ubuntu 的集成。

2.  **克隆仓库到 WSL**
    ```bash
    # 在 WSL (Ubuntu) 终端中
    git clone https://github.com/yangyaoming158/microblog.git
    cd microblog
    ```

3.  **启动 Elasticsearch 服务**
    ```bash
    docker run --name elasticsearch -d --rm -p 9200:9200 \
        -e "discovery.type=single-node" \
        -e "xpack.security.enabled=false" \
        -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" \
        docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    ```

4.  **创建并激活 Python 虚拟环境**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

5.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

6.  **配置环境变量**
    *   复制 `.env.example` (如果提供) 为 `.env`，或手动创建一个 `.env` 文件。
    *   在 `.env` 中设置 `SECRET_KEY`, `ELASTICSEARCH_URL=http://localhost:9200`, 以及你的翻译 API 凭据。
    *   `.flaskenv` 文件已包含 `FLASK_APP` 和 `FLASK_DEBUG`。

7.  **初始化/升级数据库**
    ```bash
    flask db upgrade
    ```
    
8.  **（可选）重建搜索索引**
    ```bash
    # 进入 flask shell
    flask shell
    
    # 在 Python 提示符后
    >>> from app.models import Post
    >>> Post.reindex()
    >>> exit()
    ```

9.  **运行应用**
    ```bash
    flask run
    ```
    应用现在应该运行在 `http://localhost:5000` 上，你可以直接在 Windows 的浏览器中访问。
