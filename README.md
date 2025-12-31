# Microblog: 现代化的 Flask 全栈社交平台

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Flask](https://img.shields.io/badge/Flask-3.x-green) ![Architecture](https://img.shields.io/badge/Architecture-Blueprints-orange)

本项目是基于 Miguel Grinberg 的 **Flask Mega-Tutorial** 构建的进阶版本。项目采用 **应用工厂模式** 和 **蓝图** 架构，实现了从用户认证、社交互动到全文搜索、实时翻译等全套功能，并特别针对 **Web 安全** 和 **生产环境部署** 进行了深度优化。

---

## 🏗️ 项目模块详解 (Modules & Tech Stack)

本项目采用模块化架构，将功能拆分为不同的蓝图（Blueprints）和独立的服务模块。

### 1. 🔐 认证模块 (`app/auth/`)
负责所有与用户身份验证和授权相关的逻辑。
*   **实现功能**:
    *   用户注册、登录、注销。
    *   **密码重置流程**：用户请求重置 -> 发送包含安全令牌的邮件 -> 用户点击链接重置密码。
*   **关键技术栈**:
    *   **Flask-Login**: 管理用户会话 (Session)，处理“记住我”功能。
    *   **Werkzeug Security**: 处理密码的加盐哈希 (Hashing) 存储与验证。
    *   **PyJWT (JWT)**: 生成有时效性、防篡改的密码重置令牌 (JSON Web Token)。
    *   **Flask-Mail**: 发送认证相关的电子邮件。

### 2. 🏠 核心业务模块 (`app/main/`)
包含博客平台的主要业务逻辑、视图函数和表单。
*   **实现功能**:
    *   **主页动态流**：分页显示已关注用户的帖子。
    *   **用户个人资料**：显示头像、简介、关注数/粉丝数、上次在线时间。
    *   **自定义头像**：支持用户上传本地图片，自动裁剪缩放。
    *   **社交互动**：关注/取消关注用户、发表帖子、**删除帖子**。
    *   **私信系统**：对话式私信列表、实时未读消息通知（小红点）。
*   **关键技术栈**:
    *   **Flask-WTF**: 处理所有表单的渲染与验证（CSRF 保护）。
    *   **Pillow (PIL)**: 处理用户上传的头像图片（缩放、保存）。
    *   **SQLAlchemy**: 复杂的数据库查询（如联表查询关注者帖子、私信分组）。
    *   **JavaScript (Fetch API)**: 前端轮询未读消息通知，动态更新 DOM。
    *   **Flask-Moment**: 前端时间戳的本地化渲染。

### 3. 🚫 错误处理模块 (`app/errors/`)
*   **实现功能**: 统一处理 HTTP 错误（如 404 Not Found, 500 Internal Server Error），提供友好的自定义错误页面。
*   **关键技术栈**: Flask `errorhandler` 装饰器。

### 4. 🌐 翻译服务模块 (`app/translate.py`)
*   **实现功能**:
    *   **语言检测**: 自动检测帖子内容的源语言。
    *   **实时翻译**: 将帖子内容翻译成用户当前浏览器的语言。
    *   **抽象适配器**: 封装了第三方 API 的调用细节。
*   **关键技术栈**:
    *   **百度翻译开放平台 API**: 提供底层的翻译服务。
    *   **Requests**: 发送 HTTP 请求与百度 API 通信。
    *   **Flask-Babel**: 获取当前用户的语言偏好 (`g.locale`)。

### 5. 🔍 搜索服务模块 (`app/search.py`)
*   **实现功能**:
    *   **全文搜索**: 支持对帖子内容进行关键词搜索。
    *   **索引同步**: 监听数据库事件，自动将新增/修改的帖子同步到搜索引擎索引中。
*   **关键技术栈**:
    *   **Elasticsearch**: 运行在 Docker 容器中的搜索引擎核心。
    *   **SQLAlchemy Events**: 监听 `before_commit` 和 `after_commit` 事件以触发索引更新。

### 6. 🛠️ 命令行工具 (`app/cli.py`)
*   **实现功能**: 简化开发运维工作流。
*   **关键技术栈**: **Click** (Flask CLI)。
    *   `flask translate init/update/compile`: 一键管理 `.po/.mo` 翻译文件。

---

## 🛡️ 安全特性 (Security Features)

本项目在开发过程中高度重视安全性，实施了以下防御措施：

*   **数据安全**: 敏感配置（密钥、数据库密码、API Key）全部通过 `.env` 环境变量加载，**严禁硬编码**。
*   **CSRF 防护**: 全站表单（包括 AJAX 请求）集成 Flask-WTF 的 CSRF Token 验证。
*   **XSS 防护**: Jinja2 模板自动转义，Markdown 渲染使用白名单过滤 HTML 标签。
*   **文件上传安全**: 使用 `secure_filename` 过滤文件名，严格限制文件扩展名，并重新处理图片以剥离恶意元数据。
*   **权限控制**: 敏感操作（如删除帖子）在后端进行**对象级权限检查**，防止越权访问 (IDOR)。

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
```bash
git clone <your-repo-url>
cd microblog
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. 配置环境变量
```init
SECRET_KEY=your-super-secret-key
# 数据库 (生产环境推荐 MySQL)
DATABASE_URL=mysql+pymysql://user:pass@localhost/microblog

# 邮件配置 (用于密码重置)
MAIL_SERVER=smtp.qq.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your_email@qq.com
MAIL_PASSWORD=your_auth_code

# 百度翻译 API
BAIDU_TRANSLATOR_APP_ID=your_id
BAIDU_TRANSLATOR_KEY=your_key

# Elasticsearch (可选，需启动 Docker)
# ELASTICSEARCH_URL=http://localhost:9200
```

### 3. 初始化数据库与翻译
```
# 数据库迁移
flask db upgrade

# 编译多语言文件
flask translate compile

# 创建头像存储目录
mkdir -p app/static/avatars
```

### 4. 运行
```
flask run
http://127.0.0.1:5000
```

## 🧪 测试
本项目包含完善的单元测试，使用内存数据库进行环境隔离。

## 📄 许可证
MIT License