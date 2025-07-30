# app/translate.py

import requests
import hashlib
import random
from flask import current_app # 使用 current_app 更具通用性
from flask_babel import _

LANGUAGE_MAP = {
    'es': 'spa',  # 西班牙语
    'fr': 'fra',  # 法语
    'zh': 'zh',   # 中文
    'en': 'en',   # 英语
    'de': 'de',   # 德语
    'it': 'it',   # 意大利语
    'ko': 'kor',
    # ... 根据需要添加更多映射 ...
}

def translate(text, source_language, dest_language):
    """
    使用百度翻译 API 翻译文本。
    这个函数的结构模仿了教程中微软翻译的版本。
    """

    # 1. 检查配置是否存在
    #    教程检查 'MS_TRANSLATOR_KEY'，我们检查百度的凭据。
    if not current_app.config['BAIDU_TRANSLATOR_APP_ID'] or \
       not current_app.config['BAIDU_TRANSLATOR_KEY']:
        return _('Error: the translation service is not configured.')
    
    baidu_source = LANGUAGE_MAP.get(source_language, source_language) # 映射新的语言缩写以适应百度的api
    baidu_dest = LANGUAGE_MAP.get(dest_language, dest_language)

    # 2. 准备请求所需的参数
    #    教程准备 auth headers，我们准备百度的 params 字典。
    appid = current_app.config['BAIDU_TRANSLATOR_APP_ID']
    key = current_app.config['BAIDU_TRANSLATOR_KEY']
    salt = str(random.randint(32768, 65536))
    
    # 生成签名，这是百度 API 的要求
    sign_str = appid + text + salt + key
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    # 百度翻译 API 的 URL 和请求参数
    url = 'https://api.fanyi.baidu.com/api/trans/vip/translate'
    params = {
        'q': text,
        'from': baidu_source,  # <-- 使用转换后的代码
        'to': baidu_dest,     # <-- 使用转换后的代码
        'appid': appid,
        'salt': salt,
        'sign': sign
    }
    
    # 3. 发送 HTTP 请求
    #    教程使用 requests.post()，百度 API 使用 requests.get()。
    #    我们用 try...except 来捕获网络错误，这比只检查 status_code 更健壮。
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # 检查 HTTP 状态码是否为 2xx
    except requests.exceptions.RequestException:
        # 如果发生网络错误（如超时、无法连接），返回一个通用的失败消息
        return _('Error: the translation service failed.')
        
    # 4. 解析响应并返回结果
    #    教程解析微软的 JSON 结构，我们解析百度的 JSON 结构。
    json_data = response.json()
    
    # 检查百度返回的 JSON 中是否有 error_code 字段
    if 'error_code' in json_data:
        # 如果有，说明百度服务器报告了一个具体的 API 错误
        # 我们可以返回一个更具体的错误信息，或者像教程一样返回通用信息
        return _('Error: the translation service failed.')
    
    # 如果一切正常，从 JSON 响应中提取出翻译后的文本
    # 根据百度 API 文档，结果在 'trans_result' 列表的第一个元素的 'dst' 键中
    return json_data['trans_result'][0]['dst']