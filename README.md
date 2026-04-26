# Microblog

Microblog 是一个基于 Flask 的社交博客应用，采用应用工厂模式和 Blueprint 模块化架构。当前版本包含用户认证、发帖、关注、评论、私信、按会话统计未读消息、头像上传、搜索、翻译、多语言、自动化测试、数据库迁移和 Docker 部署支持。

项目源自 Flask Mega-Tutorial 的基础结构，并在此之上补充了配置分层、输入校验、上传安全处理、迁移链修复和更完整的测试覆盖。

## 技术栈

- Python 3.10+
- Flask 3.1
- Flask-SQLAlchemy / SQLAlchemy 2.x
- Flask-Migrate / Alembic
- Flask-Login
- Flask-WTF
- Flask-Mail
- Flask-Babel
- Flask-Moment
- Pillow
- Markdown + Bleach
- Elasticsearch，可选
- 百度翻译 API，可选
- Bootstrap 5 + 自定义 CSS
- Gunicorn，Docker 运行时使用

## 主要功能

### 账号与认证

- 用户注册、登录、登出
- 记住登录状态
- 修改密码
- 邮件密码重置
- 用户名校验：必须以字母开头，只允许字母、数字、点、下划线和连字符
- 密码校验：8 到 128 个字符
- 生产环境缺少 `SECRET_KEY` 时拒绝启动

### 社交博客

- 首页展示已关注用户的动态流
- 探索页展示全站帖子
- 发帖支持标题和正文
- 正文支持 Markdown 渲染
- Markdown 输出经过 Bleach 白名单清洗
- 帖子详情页和评论功能
- 只有作者可以删除自己的帖子
- 关注和取消关注用户
- 用户主页展示头像、简介、上次在线时间、关注数和粉丝数

### 私信与通知

- 用户之间一对一私信
- 消息中心展示会话入口
- 顶部导航栏轮询未读消息通知
- 未读状态通过 `ConversationReadState` 按会话记录：
  - `user_id`：拥有该阅读状态的用户
  - `peer_id`：会话中的另一方
  - `last_read_time`：该用户最后一次读取该会话的时间
- 打开某个会话只清除该发送者的未读消息，不会误清其他发送者的未读消息

### 头像上传

- 支持 JPG、JPEG、PNG
- 上传大小由 `MAX_CONTENT_LENGTH` 控制，默认 2 MB
- 使用 Pillow 验证真实图片内容
- 自动处理 EXIF 方向
- 重新裁剪并编码为 512 x 512 图片
- 新头像保存并提交成功后，才删除旧头像

### 搜索

- 配置 `ELASTICSEARCH_URL` 时使用 Elasticsearch
- 未配置 Elasticsearch 时自动降级为数据库 LIKE 查询
- 数据库降级搜索支持正文、标题和作者用户名
- 搜索 query 有非空和长度校验

### 翻译与国际化

- 使用 `langdetect` 检测帖子语言
- 配置百度翻译 API 后可翻译文本
- 未配置翻译凭据时返回受控错误，不会导致应用崩溃
- Flask-Babel 支持 `en`、`es`、`zh`
- 通过 `flask translate init/update/compile` 管理翻译文件

## 项目结构

```text
microblog/
|-- app/
|   |-- __init__.py          # 应用工厂、扩展初始化、Blueprint 注册
|   |-- auth/                # 登录、注册、密码重置、修改密码
|   |-- main/                # 首页、帖子、评论、关注、私信、头像上传
|   |-- errors/              # 404 和 500 错误处理
|   |-- templates/           # Jinja 模板和内联样式文件
|   |-- static/avatars/      # 用户上传头像，运行时产物
|   |-- translations/        # Babel 翻译资源
|   |-- models.py            # SQLAlchemy 模型
|   |-- search.py            # Elasticsearch 适配层
|   |-- translate.py         # 百度翻译适配层
|   |-- email.py             # 异步邮件发送
|   `-- cli.py               # 翻译 CLI 命令
|-- migrations/              # Alembic 数据库迁移
|-- config.py                # 配置分层
|-- microblog.py             # Flask 入口和 shell context
|-- tests.py                 # unittest 测试
|-- Dockerfile
|-- boot.sh                  # 容器启动脚本：迁移 + Gunicorn
`-- requirements.txt
```

## 配置分层

`create_app()` 支持三种配置方式：

- `create_app()`：读取 `FLASK_CONFIG`，默认使用开发配置
- `create_app('testing')`：按名称选择配置
- `create_app(TestConfig)`：直接传入配置类

当前配置类：

| 配置类 | 用途 | 关键行为 |
| --- | --- | --- |
| `DevConfig` | 本地开发 | `DEBUG=True`，开发密钥缺省为 `you-will-never-guess` |
| `TestConfig` | 自动化测试 | 内存 SQLite，关闭 CSRF，禁用 Elasticsearch、邮件发送和外部翻译服务 |
| `ProductionConfig` | 生产环境 | 必须设置 `SECRET_KEY`，否则拒绝启动 |

支持的 `FLASK_CONFIG` 值：

```text
development, dev, testing, test, production, prod
```

## 环境变量

本地开发可创建 `.env` 文件。该文件已被 `.gitignore` 忽略，不应提交。

```ini
FLASK_APP=microblog.py
FLASK_CONFIG=development
SECRET_KEY=replace-me

# 数据库。未设置时默认使用项目根目录下的 app.db
# DATABASE_URL=sqlite:////absolute/path/to/app.db
# DATABASE_URL=mysql+pymysql://user:password@host/database

# 邮件，用于密码重置
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password-or-token
ADMINS=admin@example.com

# 可选：百度翻译
BAIDU_TRANSLATOR_APP_ID=your-app-id
BAIDU_TRANSLATOR_KEY=your-key

# 可选：Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200

# 可选运行参数
POSTS_PER_PAGE=10
MAX_CONTENT_LENGTH=2097152
AVATAR_UPLOAD_DIR=/absolute/path/to/avatars
```

生产环境至少需要：

```ini
FLASK_APP=microblog.py
FLASK_CONFIG=production
SECRET_KEY=a-long-random-secret
DATABASE_URL=your-production-database-url
```

## 本地运行

```bash
cd microblog
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=microblog.py
export FLASK_CONFIG=development
flask db upgrade
flask translate compile
flask run
```

访问地址：

```text
http://127.0.0.1:5000
```

Elasticsearch 和百度翻译都是可选服务。没有 Elasticsearch 时，搜索会使用数据库降级查询；没有百度翻译凭据时，翻译接口会返回受控的服务未配置错误。

## 数据库迁移

常规升级命令：

```bash
flask db upgrade
```

当前迁移链包含一个恢复的历史迁移：

```text
e2e2a8858e20_add_user_activation_fields.py
```

这个 revision 对应 `user` 表中已有的 `is_active` 和 `activation_token` 字段。不要删除它，否则已有数据库可能再次出现以下错误：

```text
Can't locate revision identified by 'e2e2a8858e20'
```

私信按会话未读模型的迁移是：

```text
9c3b0d8f4a21_conversation_read_state.py
```

它会创建 `conversation_read_state` 表，用于保存每个会话的最后读取时间。

## 测试

项目当前使用 `unittest`，测试配置来自 `config.TestConfig`。

```bash
source venv/bin/activate
python tests.py
```

当前测试覆盖：

- 密码哈希
- 注册、登录、登出
- 修改密码
- 用户名和密码校验
- 关注关系和关注流
- 发帖和搜索降级
- 删除帖子权限
- 评论
- 用户弹窗
- 私信和未读通知
- 按发送者隔离的会话已读状态
- 头像上传和非法图片拒绝
- 翻译服务未配置和 malformed JSON
- 配置选择、测试环境隔离、生产 `SECRET_KEY` 校验

当前基线：

```text
21 tests OK
```

## Docker

构建镜像：

```bash
docker build -t microblog .
```

运行容器：

```bash
docker run --rm -p 5000:5000 --env-file .env microblog
```

`boot.sh` 会在容器启动时执行：

```bash
flask db upgrade
gunicorn -b :5000 --access-logfile - --error-logfile - microblog:app
```

生产容器建议使用外部数据库，并通过 `DATABASE_URL` 指向它。如果在 Docker 内使用 SQLite，需要挂载持久化目录，否则容器删除后数据也会丢失。

## Git 与运行时文件

以下内容属于运行时或本地环境文件，不应提交：

- `.env`
- `.flaskenv`
- `app.db`
- `logs/`
- `*.log`
- `app/static/avatars/*`
- `messages.pot`
- 编译后的 `*.mo` 文件
- `venv/`
- `__pycache__/`

迁移文件必须提交，尤其是已经被数据库引用过的 revision。

## 常见问题

### `Can't locate revision identified by ...`

说明数据库的 `alembic_version` 表指向了一个当前 `migrations/versions` 中不存在的 revision。如果需要保留数据，应恢复缺失的迁移文件；只有在确认数据库结构和目标 revision 完全一致后，才谨慎使用 Alembic stamp。

### `SECRET_KEY must be set`

`ProductionConfig` 要求生产环境必须设置 `SECRET_KEY`：

```bash
export FLASK_CONFIG=production
export SECRET_KEY='a-long-random-secret'
```

### 翻译不可用

检查 `.env` 中是否设置：

```ini
BAIDU_TRANSLATOR_APP_ID=...
BAIDU_TRANSLATOR_KEY=...
```

未设置时，应用仍会正常运行，只是翻译接口会返回服务未配置的错误。

### 搜索没有 Elasticsearch 结果

如果没有设置 `ELASTICSEARCH_URL`，应用会自动使用数据库降级搜索。如果已经设置，请确认 Elasticsearch 服务可访问，并在需要时重建索引。

## 许可证

MIT License
