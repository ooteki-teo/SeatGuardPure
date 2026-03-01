"""
截图功能模块
"""

import os
import sys
import time
import cv2
import logging

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """截图捕获器"""

    @staticmethod
    def capture_screenshot(frame, config, log_callback=None, prefix="capture"):
        """
        捕获截图并保存到日志目录

        Args:
            frame: 摄像头帧
            config: 配置对象
            log_callback: 日志回调函数
            prefix: 文件名前缀
        """
        # 检查截图功能是否启用
        if not config.screenshot_enabled:
            return

        def log(message):
            if log_callback:
                log_callback(message)
            logger.info(message)

        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np

            # 获取日志目录
            log_dir = os.path.dirname(os.path.abspath(__file__))
            if hasattr(sys, '_MEIPASS'):
                log_dir = os.path.dirname(sys.executable)

            # 创建 capture 子目录
            capture_dir = os.path.join(log_dir, "capture")
            if not os.path.exists(capture_dir):
                os.makedirs(capture_dir)

            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.jpg"
            filepath = os.path.join(capture_dir, filename)

            # 转换帧为 PIL 图像
            if frame is not None:
                # OpenCV BGR 转 RGB
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = frame

                img = Image.fromarray(frame_rgb)

                # 添加时间戳水印
                draw = ImageDraw.Draw(img)
                time_text = time.strftime("%Y-%m-%d %H:%M:%S")

                # 尝试使用系统字体
                try:
                    font = ImageFont.truetype("arial.ttf", 24)
                except:
                    font = ImageFont.load_default()

                # 绘制半透明背景
                bbox = draw.textbbox((0, 0), time_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                draw.rectangle([10, 10, 10 + text_width + 20, 10 + text_height + 20], fill=(0, 0, 0, 128))

                # 绘制文字
                draw.text((20, 20), time_text, fill=(255, 255, 255), font=font)

                # 保存图片
                img.save(filepath, "JPEG", quality=85)
                log(f"截图已保存: {filename}")
        except Exception as e:
            log(f"截图失败: {e}")
