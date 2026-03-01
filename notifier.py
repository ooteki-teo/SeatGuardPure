"""
提醒模块 - 使用 Windows 原生通知
"""

import threading
import sys
import os
import ctypes  # 强制暴露 ctypes 依赖

# 全局导入，让 PyInstaller 能扫描到
try:
    from win10toast import ToastNotifier
    HAS_WIN10TOAST = True
except ImportError:
    HAS_WIN10TOAST = False

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False


class Notifier:
    """提醒管理器"""

    def __init__(self, log_callback=None):
        self.reminded = False
        self.log_callback = log_callback

    def set_log_callback(self, callback):
        """设置日志回调"""
        self.log_callback = callback

    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)
        # 使用 try-except 防止在 console=False 时崩溃
        try:
            print(f"[Notifier] {message}")
        except Exception:
            pass

    def notify(self, title="座位提醒", message="想要活得久，喝杯水！站起来！"):
        """
        发送提醒

        Args:
            title: 提醒标题
            message: 提醒内容
        """
        self.reminded = True

        self.log(f"发送通知: {title} - {message}")

        # 在后台线程中发送通知
        thread = threading.Thread(target=self._send_notification, args=(title, message), daemon=True)
        thread.start()

    def _send_notification(self, title, message):
        """发送系统通知"""
        # 方法1: win10toast
        if HAS_WIN10TOAST:
            try:
                self.log("尝试使用 win10toast...")
                toaster = ToastNotifier()
                toaster.show_toast(
                    title,
                    message,
                    duration=10,
                    threaded=True
                )
                self.log("win10toast 通知发送成功")
                return
            except Exception as e:
                self.log(f"win10toast 失败: {e}")

        # 方法2: plyer
        if HAS_PLYER:
            try:
                self.log("尝试使用 plyer...")
                notification.notify(
                    title=title,
                    message=message,
                    app_name='SeatGuard',
                    timeout=10
                )
                self.log("plyer 通知发送成功")
                return
            except Exception as e:
                self.log(f"plyer 失败: {e}")

        # 方法3: ctypes 消息框
        try:
            self.log("尝试使用消息框...")
            MB_OK = 0x0
            MB_ICONINFORMATION = 0x40
            result = ctypes.windll.user32.MessageBoxW(None, message, title, MB_OK | MB_ICONINFORMATION)
            self.log(f"消息框已显示, result={result}")
        except Exception as e:
            self.log(f"消息框也失败: {e}")

    def reset(self):
        """重置提醒状态"""
        self.reminded = False
