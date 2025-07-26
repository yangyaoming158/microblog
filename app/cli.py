import os
import click
from flask import Blueprint

# 本代码用于简化合并繁琐的翻译指令

# flask translate init <language-code> 用于初始化要载入语言库的语言
# flask translate update 用于更新工程文件中出现的文本更新内容
# flask translate compile 用于编译导入的新语言或者更新的内容

bp = Blueprint('cli', __name__, cli_group=None)

@bp.cli.group()
def translate():
    """Translation and localization commands."""
    pass

@translate.command()
@click.argument('lang')
def init(lang):
    """Initialize a new language."""
    if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'): # 一个前提指令，创建对应的语言文件前创建一个最基本的messages.pot
        raise RuntimeError('extract command failed')
    if os.system(
            'pybabel init -i messages.pot -d app/translations -l ' + lang):
        raise RuntimeError('init command failed')
    os.remove('messages.pot')


@translate.command()
def update():
    """Update all languages."""
    if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
        raise RuntimeError('extract command failed')
    if os.system('pybabel update -i messages.pot -d app/translations'):
        raise RuntimeError('update command failed')
    os.remove('messages.pot')


@translate.command()
def compile():
    """Compile all languages."""
    if os.system('pybabel compile -d app/translations'):
        raise RuntimeError('compile command failed')