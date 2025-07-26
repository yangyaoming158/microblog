# Microblog - Flask Mega-Tutorial 学习项目

这是一个跟随 Miguel Grinberg 的 [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) 教程构建的微博客应用。该项目旨在学习和实践使用 Flask 构建一个功能齐全的 Web 应用的全过程。

## 关于 `chapter15-refactor` 分支

这个分支代表了项目在完成教程第十五章后的一次重大**架构重构**。其核心目标是为了提升应用的可维护性、可测试性和可扩展性，为未来向更大型应用演进打下坚实的基础。

主要的架构变更包括：

1.  **应用工厂模式 (Application Factory Pattern):**
    *   移除了全局的应用实例 (`app = Flask(...)`)。
    *   引入了 `create_app()` 工厂函数，用于在运行时动态地创建和配置应用实例。
    *   这极大地提升了测试的灵活性和可靠性，允许为每个测试用例创建独立的、使用特定配置的应用。

2.  **蓝图 (Blueprints):**
    *   将原有的、按文件类型组织的结构，重构为了按**功能模块**组织的结构。
    *   应用被拆分成了三个核心蓝图：
        *   **`main`**: 包含核心的应用功能，如主页、发现页、用户个人资料等。
        *   **`auth`**: 封装了所有与用户认证相关的功能，包括登录、登出、注册和密码重置。
        *   **`errors`**: 封装了自定义的错误页面处理器（如 404 和 500）。
    *   这种结构使得功能边界清晰，代码内聚性更高，更易于复用和维护。

## 功能列表

本项目实现了以下功能：

*   用户认证系统：注册、登录、登出、密码重置。
*   用户个人资料：个人简介、头像 (Gravatar)、上次在线时间。
*   关注系统：用户可以互相关注。
*   动态流：主页显示已关注用户的帖子。
*   帖子发布与分页显示。
*   全文搜索功能。
*   国际化 (i18n) 与本地化 (l10n)，支持英语、西班牙语和中文。
*   通过 Ajax 实现的实时动态翻译功能。
*   通过邮件发送错误报告和密码重置链接。
*   完善的单元测试覆盖。
*   通过自定义 CLI 命令简化开发工作流。

## 技术栈

*   **后端:** Python, Flask
*   **数据库:** Flask-SQLAlchemy (ORM), Flask-Migrate (数据库迁移)
*   **表单:** Flask-WTF
*   **用户认证:** Flask-Login
*   **国际化:** Flask-Babel
*   **邮件:** Flask-Mail
*   **前端:** HTML, Bootstrap, Jinja2, Moment.js (通过 Flask-Moment)
*   **测试:** `unittest`
*   **命令行:** Click (通过 Flask)

## 如何运行

1.  **克隆仓库**
    ```bash
    git clone https://github.com/your-username/microblog.git
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
    *   复制 `.env.example` (如果提供) 或手动创建一个 `.env` 文件。
    *   在 `.env` 文件中设置必要的环境变量，如 `SECRET_KEY` 和翻译服务的 API 密钥。
    *   `.flaskenv` 文件已包含 `FLASK_APP` 和 `FLASK_DEBUG` 的基本配置。

5.  **初始化并升级数据库**
    ```bash
    flask db upgrade
    ```

6.  **运行应用**
    ```bash
    flask run
    ```

7.  **运行翻译命令 (如果需要)**
    ```bash
    # 更新翻译文件
    flask translate update
    # 编译翻译文件
    flask translate compile
    ```

## 运行单元测试
```bash
python tests.py
```
