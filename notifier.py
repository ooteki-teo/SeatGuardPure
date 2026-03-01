"""
提醒模块 - 支持 Windows 和 macOS 原生通知
"""

import threading
import sys
import os
import platform
import ctypes

# 强制暴露依赖，让 PyInstaller 能扫描到
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


def _get_system():
    """获取当前操作系统"""
    return platform.system()


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
        system = _get_system()

        # ===== macOS 通知 =====
        if system == "Darwin":
            # 方法1: 使用 osascript 调用 macOS 通知中心
            try:
                self.log("尝试使用 macOS 通知...")
                script = f'display notification "{message}" with title "{title}"'
                os.system(f"osascript -e '{script}'")
                self.log("macOS 通知发送成功")
                return
            except Exception as e:
                self.log(f"osascript 通知失败: {e}")

            # 方法2: plyer (跨平台)
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

            # 方法3: terminal-notifier (macOS 常用工具)
            try:
                self.log("尝试使用 terminal-notifier...")
                os.system(f'terminal-notifier -title "{title}" -message "{message}" -appIcon SeatGuard')
                self.log("terminal-notifier 通知发送成功")
                return
            except Exception as e:
                self.log(f"terminal-notifier 失败: {e}")

        # ===== Windows 通知 =====
        elif system == "Windows":
            # 方法1: win10toast
            if HAS_WIN10TOAST:
                try:
                    self.log("尝试使用 win10toast...")
                    toaster = ToastNotifier()
                    toaster.show_toast(
                        title,
                        message,
                        duration=10,
                        threaded=False  # 改为非线程模式，避免后台线程异常
                    )
                    self.log("win10toast 通知发送成功")
                    return
                except Exception as e:
                    # 静默处理 win10toast 的已知错误，避免日志刷屏
                    error_str = str(e)
                    if "classAtom" in error_str or "WNDPROC" in error_str or "WPARAM" in error_str:
                        pass  # 静默忽略已知错误
                    else:
                        self.log(f"win10toast 失败: {e}")

            # 方法2: plyer (跨平台)
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

            # 方法3: ctypes 消息框 (Windows 特定)
            try:
                self.log("尝试使用消息框...")
                MB_OK = 0x0
                MB_ICONINFORMATION = 0x40
                result = ctypes.windll.user32.MessageBoxW(None, message, title, MB_OK | MB_ICONINFORMATION)
                self.log(f"消息框已显示, result={result}")
            except Exception as e:
                self.log(f"消息框也失败: {e}")

        # ===== Linux 通知 =====
        else:
            # 使用 plyer (跨平台)
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

            # 使用 notify-send (Linux 常用工具)
            try:
                self.log("尝试使用 notify-send...")
                os.system(f'notify-send "{title}" "{message}"')
                self.log("notify-send 通知发送成功")
                return
            except Exception as e:
                self.log(f"notify-send 失败: {e}")

    def reset(self):
        """重置提醒状态"""
        self.reminded = False
