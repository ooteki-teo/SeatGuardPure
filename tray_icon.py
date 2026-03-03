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
        # 1. PyInstaller 打包后的临时目录优先
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            if os.path.exists(icon_path):
                return icon_path

        # 2. 当前目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, 'icon.ico')
        if os.path.exists(icon_path):
            return icon_path

        # 3. 项目根目录
        root_dir = os.path.dirname(base_dir)
        icon_path = os.path.join(root_dir, 'icon.ico')
        if os.path.exists(icon_path):
            return icon_path

        # 4. exe 所在目录（打包后 exe 旁边）
        if hasattr(sys, '_MEIPASS'):
            exe_dir = os.path.dirname(sys.executable)
            icon_path = os.path.join(exe_dir, 'icon.ico')
            if os.path.exists(icon_path):
                return icon_path

        return None

    @staticmethod
    def get_icon_path_by_state(state, is_running=True):
        """
        根据状态获取对应图标路径

        Args:
            state: 状态字符串 ('work', 'relax', 'check', 'away')，或 None 表示未运行
            is_running: 是否运行中

        Returns:
            图标文件路径
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(base_dir, 'icons')

        # 如果未运行，使用 not_moniter 图标
        if not is_running or state is None:
            icon_filename = 'not_moniter-001.ico'
            icon_path = os.path.join(icons_dir, icon_filename)
            if os.path.exists(icon_path):
                return icon_path
            return TrayIconFactory.get_icon_path()

        # 根据状态选择图标文件
        icon_mapping = {
            'work': 'icon_work-001.ico',
            'relax': 'icon_relax-001.ico',
            'check': 'icon_check-001.ico',
            'away': 'icon_away-001.ico',
        }

        icon_filename = icon_mapping.get(state, 'icon_work-001.ico')
        icon_path = os.path.join(icons_dir, icon_filename)

        # 检查图标是否存在
        if os.path.exists(icon_path):
            return icon_path

        # 如果状态图标不存在，回退到默认图标
        return TrayIconFactory.get_icon_path()

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

    @staticmethod
    def create_state_icon(state, is_running=True, log_callback=None):
        """
        根据状态创建托盘图标

        Args:
            state: 状态字符串 ('work', 'relax', 'check', 'away')
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
            from PIL import Image

            # 根据状态获取对应图标路径
            icon_path = TrayIconFactory.get_icon_path_by_state(state, is_running)

            if icon_path and os.path.exists(icon_path):
                img = Image.open(icon_path)
                # 调整大小为 64x64
                img = img.resize((64, 64), Image.LANCZOS)
                # 转换为 RGBA 模式
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                return img

            # 如果没有找到图标，创建默认图标
            return TrayIconFactory.create_tray_icon(is_running, log_callback)

        except Exception as e:
            log(f"创建状态图标失败: {e}")
            return TrayIconFactory.create_default_icon()
