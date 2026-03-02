#!/usr/bin/env python3
"""
SeatGuard 打包脚本
使用 PyInstaller 将 Python 代码打包成 Windows 可执行文件
"""

import os
import sys
import shutil
import subprocess

# 解决 Windows 控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")

# 打包输出文件名
APP_NAME = "SeatGuardPure"
EXE_NAME = f"{APP_NAME}.exe"
MAIN_SCRIPT = "main.py"

# 图标路径
ICON_PATH = os.path.join(PROJECT_ROOT, "icon.ico")

# OpenCV 级联分类器文件
HAARCASCADE_FILE = "haarcascade_frontalface_default.xml"
HAARCASCADE_PATH = os.path.join(PROJECT_ROOT, "resources", HAARCASCADE_FILE)

# Web 前端目录
WEB_DIR = os.path.join(PROJECT_ROOT, "web")


def clean_build():
    """清理旧的构建文件"""
    print("[clean] 清理旧构建文件...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    print("[ok] 清理完成")


def check_dependencies():
    """检查依赖是否安装"""
    print("[deps] 检查依赖...")
    try:
        import PyInstaller
        print(f"[ok] PyInstaller 已安装: {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_exe():
    """使用 PyInstaller 打包"""
    print("[build] 开始打包...")

    # PyInstaller 命令参数
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",  # 打包成单个exe文件
        "--windowed",  # 不显示控制台窗口
        "--icon", ICON_PATH if os.path.exists(ICON_PATH) else None,
        "--add-data", f"resources{os.pathsep}resources",  # 添加资源文件夹
        "--add-data", f"{HAARCASCADE_PATH}{os.pathsep}.",  # 添加级联分类器
        "--add-data", f"{ICON_PATH}{os.pathsep}.",  # 添加图标文件
        "--add-data", f"web{os.pathsep}web",  # 添加 Web 前端目录
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--hidden-import", "plyer",
        "--hidden-import", "pystray",
        "--hidden-import", "requests",
        "--collect-all", "pystray",
        "--collect-all", "plyer",
        "--collect-all", "fastapi",
        "--collect-all", "uvicorn",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--clean",
        MAIN_SCRIPT,
    ]

    # 过滤掉 None 的参数
    args = [arg for arg in args if arg is not None]

    print(f"[cmd] {' '.join(args)}")

    # 执行打包
    result = subprocess.run(args, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print("[err] 打包失败!")
        sys.exit(1)

    print("[ok] 打包完成!")


def verify_exe():
    """验证生成的 exe 文件"""
    # --onefile 模式：exe 在 dist 目录下
    exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")

    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"[ok] EXE 文件已生成: {exe_path}")
        print(f"[size] 文件大小: {size_mb:.2f} MB")

        print("\n[info] PyInstaller --onefile 模式下:")
        print("  - 资源文件被打包进 exe 中")
        print("  - 运行时会自动解压到临时目录")
        print("  - _MEIPASS 会指向临时解压目录")
        return True
    else:
        print(f"[err] EXE 文件未找到: {exe_path}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("SeatGuard 打包工具")
    print("=" * 50)

    # 检查依赖
    check_dependencies()

    # 清理旧构建
    clean_build()

    # 执行打包
    build_exe()

    # 验证结果
    if verify_exe():
        print("\n" + "=" * 50)
        print("打包成功!")
        print(f"输出目录: {DIST_DIR}")
        print(f"可执行文件: {EXE_NAME}")
        print("=" * 50)
    else:
        print("\n打包失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
