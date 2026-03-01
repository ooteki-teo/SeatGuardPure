"""
Windows 开机自启管理模块
"""
import os
import sys
import winreg


class AutoStartManager:
    def __init__(self, app_name="SeatGuard"):
        self.app_name = app_name
        # 判断当前是 Python 脚本运行，还是 PyInstaller 打包后的 .exe 运行
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe，获取 exe 的绝对路径
            self.exe_path = sys.executable
        else:
            # 如果是代码运行，获取 main.py 的绝对路径（仅测试用）
            self.exe_path = os.path.abspath(sys.argv[0])

        # 写入当前用户的开机启动项注册表路径（无需管理员权限）
        self.registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def is_enabled(self):
        """检查是否已开启开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return value == self.exe_path
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def enable(self):
        """开启开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.exe_path)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"开启自启失败: {e}")
            return False

    def disable(self):
        """关闭开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return True  # 本来就没有，视为关闭成功
        except Exception as e:
            print(f"关闭自启失败: {e}")
            return False
