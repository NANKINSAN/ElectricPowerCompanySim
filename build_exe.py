"""
自動 exe 化および配布パッケージ作成スクリプト
使い方:
    python build_exe.py
または
    build_exe.bat を実行
"""
import subprocess
import shutil
import os
import sys

def build():
    print("=" * 60)
    print(" 電力運用シミュレータ (PowerGridSim) exe化ビルド開始")
    print("=" * 60)

    # 1. PyInstallerの実行
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "PowerGridSim.spec"
    ]
    print(f"実行コマンド: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[ERROR] PyInstaller のビルドに失敗しました。")
        sys.exit(1)

    dist_dir = os.path.join("dist", "PowerGridSim")
    print(f"\n[INFO] 配布フォルダ '{dist_dir}' を整備しています...")

    # 2. ユーザーが外部から編集できるように config.json, scenario.json をコピー
    files_to_copy = ["config.json", "scenario.json"]
    for f in files_to_copy:
        if os.path.exists(f):
            dest = os.path.join(dist_dir, f)
            shutil.copy2(f, dest)
            print(f"  -> コピー完了: {f}")

    # 3. プレイヤー向け説明書 (README_PLAYER.md) を配布用の README.md としてコピー
    if os.path.exists("README_PLAYER.md"):
        dest_readme = os.path.join(dist_dir, "README.md")
        shutil.copy2("README_PLAYER.md", dest_readme)
        print("  -> コピー完了: README_PLAYER.md -> dist/README.md (プレイヤー向け説明書)")
    elif os.path.exists("README.md"):
        dest_readme = os.path.join(dist_dir, "README.md")
        shutil.copy2("README.md", dest_readme)
        print("  -> コピー完了: README.md")

    # assets フォルダも念のため配置（ユーザーが追加アセットを入れられるように）
    dest_assets = os.path.join(dist_dir, "assets")
    os.makedirs(dest_assets, exist_ok=True)
    if os.path.exists(os.path.join("assets", "umplus_j10r.bdf")):
        shutil.copy2(os.path.join("assets", "umplus_j10r.bdf"), os.path.join(dest_assets, "umplus_j10r.bdf"))
        print("  -> コピー完了: assets/umplus_j10r.bdf")

    print("\n" + "=" * 60)
    print(" [SUCCESS] ビルド完了！")
    print(f" 配布用フォルダ: {os.path.abspath(dist_dir)}")
    print(f" 実行ファイル  : {os.path.abspath(os.path.join(dist_dir, 'PowerGridSim.exe'))}")
    print(" ※ dist/PowerGridSim フォルダをそのままZIP等で配布できます。")
    print("=" * 60)

if __name__ == "__main__":
    build()
