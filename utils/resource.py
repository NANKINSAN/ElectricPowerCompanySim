"""
リソースおよび設定ファイルのパス解決ユーティリティ
PyInstaller による exe 化後（ワンファイル/ディレクトリ配布）でも、
内部アセットおよび外部のユーザー編集用設定ファイル（config.json, scenario.json）を
正しく安全に読み書きできるようにパスを決定する。
"""
import sys
import os

def get_base_dir() -> str:
    """実行環境のベースディレクトリを取得（exe実行時はexeのある場所）"""
    if getattr(sys, "frozen", False):
        # exeとして実行されている場合
        return os.path.dirname(sys.executable)
    else:
        # 通常のスクリプト実行時
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bundle_dir() -> str:
    """PyInstallerの一時展開先（_MEIPASS）またはプロジェクトルートを取得"""
    return getattr(sys, "_MEIPASS", get_base_dir())

def get_resource_path(relative_path: str) -> str:
    """
    画像・フォント・音声などのアセットパスを取得
    1. _MEIPASS（exe内蔵）
    2. exeと同じフォルダの相対パス
    3. カレントディレクトリ
    """
    # 1. バンドル内部
    p1 = os.path.join(get_bundle_dir(), relative_path)
    if os.path.exists(p1):
        return p1
        
    # 2. exe直下のフォルダ
    p2 = os.path.join(get_base_dir(), relative_path)
    if os.path.exists(p2):
        return p2

    # 3. カレントディレクトリ
    if os.path.exists(relative_path):
        return os.path.abspath(relative_path)

    return p1

def get_config_path(filename: str) -> str:
    """
    ユーザーが編集可能な設定ファイル（config.json, scenario.json）のパスを取得
    ユーザーが編集できるように、exe直下のファイル（またはカレントディレクトリ）を最優先する。
    見つからなければバンドル内部を探す。
    """
    # 1. カレントディレクトリ
    if os.path.exists(filename):
        return os.path.abspath(filename)

    # 2. exeのあるディレクトリ直下
    p_exe = os.path.join(get_base_dir(), filename)
    if os.path.exists(p_exe):
        return p_exe

    # 3. バンドル内部（デフォルト値）
    p_bundle = os.path.join(get_bundle_dir(), filename)
    if os.path.exists(p_bundle):
        return p_bundle

    # デフォルトはexe直下
    return p_exe
