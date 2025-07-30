# app/search.py
# 这个模块封装了所有与 Elasticsearch 交互的底层逻辑，
# 充当了应用其余部分与搜索引擎之间的“中间人”或“适配器”。

from flask import current_app

def add_to_index(index, model):
    """
    将一个 SQLAlchemy 模型对象添加到指定的 Elasticsearch 索引中。
    这个函数既可以用于创建新文档，也可以用于更新已存在的文档。
    抽象层设计：隔离依赖 (app/search.py)
    做什么： 创建一个 search.py 模块，将所有与 Elasticsearch 直接交互的底层代码（连接、索引、删除、搜索）封装成三个通用的函数 (add_to_index, remove_from_index, query_index)。
    为什么（核心思想）： 这是抽象和解耦。应用的其他部分（如模型、路由）不再需要知道我们用的是 Elasticsearch。它们只调用 search.py 提供的简单接口。
    好处： 如果未来想把 Elasticsearch 换成其他搜索引擎，只需要重写 search.py 这一个文件，整个应用的其他部分无需改动，极大地提高了代码的可维护性和可替换性。

    Args:
        index (str): 目标 Elasticsearch 索引的名称 (通常是模型的 __tablename__)。
        model: 待索引的 SQLAlchemy 模型实例 (例如，一个 Post 对象)。
    """
    # 1. 优雅降级检查：
    #    检查 Elasticsearch 客户端是否已被配置和初始化。
    #    如果没有 (比如在 .env 中没有设置 ELASTICSEARCH_URL)，则直接返回，
    #    让应用在没有搜索功能的情况下也能正常运行。
    if not current_app.elasticsearch:
        return

    # 2. 构建文档内容 (Payload):
    #    创建一个空字典，用来存放需要被索引的数据。
    payload = {}
    # 遍历模型中定义的 `__searchable__` 列表 (例如，在 Post 模型中是 ['body'])。
    for field in model.__searchable__:
        # getattr(model, field) 是一个 Python 内置函数，
        # 作用是获取一个对象的属性值。例如，getattr(post, 'body') 就等于 post.body。
        # 我们将模型中可搜索字段的值，填充到 payload 字典中。
        payload[field] = getattr(model, field)
    
    # 3. 执行索引操作：
    #    调用 Elasticsearch 客户端的 index() 方法。
    #    - index=index: 指定要写入的索引名称，如 'post'。
    #    - id=model.id: 【关键】使用 SQLAlchemy 模型的 ID 作为 Elasticsearch 文档的唯一 ID。
    #                   这使得两个数据库的记录可以一一对应。
    #    - document=payload: 要索引的文档内容。
    current_app.elasticsearch.index(index=index, id=model.id, document=payload)

def remove_from_index(index, model):
    """
    从指定的 Elasticsearch 索引中移除一个文档。

    Args:
        index (str): 目标 Elasticsearch 索引的名称。
        model: 待移除的 SQLAlchemy 模型实例。
    """
    # 同样进行优雅降级检查。
    if not current_app.elasticsearch:
        return
    
    # 调用 Elasticsearch 客户端的 delete() 方法。
    # 通过传入索引名和与 SQLAlchemy 记录相同的 ID，来精确定位并删除文档。
    current_app.elasticsearch.delete(index=index, id=model.id)

def query_index(index, query, page, per_page):
    """
    在指定的 Elasticsearch 索引中执行全文搜索查询。

    Args:
        index (str): 要搜索的索引名称。
        query (str): 用户的搜索查询字符串 (例如："hello world")。
        page (int): 请求的页码，用于分页。
        per_page (int): 每页显示的结果数量。

    Returns:
        tuple: 一个包含两部分的元组 (ids, total)。
               - ids (list[int]): 按相关度排序的、匹配到的文档的 ID 列表。
               - total (int): 匹配到的结果总数。
    """
    # 同样进行优雅降级检查。如果 ES 不可用，返回一个空结果。
    if not current_app.elasticsearch:
        return [], 0
    
    # 调用 Elasticsearch 客户端的 search() 方法执行搜索。
    search = current_app.elasticsearch.search(
        index=index, # 指定在哪个索引中搜索
        
        # 定义查询体 (Query Body)
        query={
            'multi_match': { # 使用 'multi_match' 查询类型
                'query': query,    # 用户的原始搜索词
                'fields': ['*']  # 在【所有】可搜索字段中进行匹配 (由 `__searchable__` 决定)
            }
        },
        
        # 实现分页
        # from_: 从第几条结果开始返回 (注意 'from' 是 Python 关键字，所以参数名带下划线)
        # size:  本次查询最多返回多少条结果
        from_=(page - 1) * per_page,
        size=per_page
    )
    
    # 从复杂的 Elasticsearch 响应中，提取出我们需要的 ID 列表。
    # search['hits']['hits'] 是一个包含了所有命中结果的列表。
    # hit['_id'] 是每个结果的文档 ID (它是一个字符串)。
    # 我们使用列表推导式来遍历结果，并将字符串 ID 转换为整数。
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    
    # 从响应中提取出匹配到的结果总数。
    total = search['hits']['total']['value']
    
    # 返回 ID 列表和总数，供上层逻辑 (如 SearchableMixin) 使用。
    return ids, total