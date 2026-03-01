"""
托盘图标模块
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)


class TrayIconFactory:
    """托盘图标工厂"""

    @staticmethod
    def get_icon_path():
        """获取图标路径"""
        # 1. 当前目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, 'icon.ico')
        if os.path.exists(icon_path):
            return icon_path

        # 2. 项目根目录
        root_dir = os.path.dirname(base_dir)
        icon_path = os.path.join(root_dir, 'icon.ico')
        if os.path.exists(icon_path):
            return icon_path

        # 3. PyInstaller 打包后的临时目录
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            if os.path.exists(icon_path):
                return icon_path
            # 4. 打包后的根目录（resources文件夹）
            icon_path = os.path.join(os.path.dirname(sys._MEIPASS), 'icon.ico')
            if os.path.exists(icon_path):
                return icon_path

        return None

    @staticmethod
    def create_tray_icon(is_running, log_callback=None):
        """
        创建托盘图标

        Args:
            is_running: 是否运行中
            log_callback: 日志回调函数

        Returns:
            PIL Image 对象
        """
        def log(message):
            if log_callback:
                log_callback(message)
            logger.info(message)

        try:
            from PIL import Image, ImageDraw

            # 尝试加载 icon.ico 文件
            icon_path = TrayIconFactory.get_icon_path()
            if icon_path and os.path.exists(icon_path):
                img = Image.open(icon_path)
                # 调整大小为 64x64（托盘图标标准大小）
                img = img.resize((64, 64), Image.LANCZOS)
                # 转换为 RGBA 模式（pystray 在 Windows 上需要 RGBA）
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                return img

            # 如果没有 icon.ico，创建默认图标
            size = 64
            img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            if is_running:
                # 绿色圆圈 - 运行中
                draw.ellipse([8, 8, 56, 56], fill='#27AE60', outline='#1E8449', width=2)
            else:
                # 灰色圆圈 - 未运行
                draw.ellipse([8, 8, 56, 56], fill='#95A5A6', outline='#7F8C8D', width=2)

            # 返回 RGBA 图像
            return img
        except Exception as e:
            log(f"创建图标失败: {e}")
            return None

    @staticmethod
    def create_default_icon():
        """创建默认图标（用于托盘创建失败时）"""
        try:
            from PIL import Image, ImageDraw
            icon_image = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
            draw = ImageDraw.Draw(icon_image)
            draw.ellipse([8, 8, 56, 56], fill='#95A5A6', outline='#7F8C8D', width=2)
            return icon_image
        except Exception:
            return None
