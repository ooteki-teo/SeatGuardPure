"""
跨平台开机自启管理模块
支持 Windows、macOS 和 Linux
"""
import os
import sys
import platform
import shutil
import plistlib


class AutoStartManager:
    def __init__(self, app_name="SeatGuard"):
        self.app_name = app_name
        self.system = platform.system()

        # 判断当前是 Python 脚本运行，还是 PyInstaller 打包后的 .exe 运行
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe，获取 exe 的绝对路径
            self.exe_path = sys.executable
        else:
            # 如果是代码运行，获取 main.py 的绝对路径
            self.exe_path = os.path.abspath(sys.argv[0])

        # 获取应用支持目录
        self._setup_directories()

    def _setup_directories(self):
        """根据操作系统设置自启动目录和配置文件路径"""
        home = os.path.expanduser("~")

        if self.system == "Windows":
            # Windows: 使用注册表
            self.registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            self.enabled_path = None  # 使用注册表，无需文件路径

        elif self.system == "Darwin":
            # macOS: 使用 launchd plist
            self.launch_agent_dir = os.path.join(home, "Library", "LaunchAgents")
            self.plist_filename = f"com.{self.app_name.lower()}.plist"
            self.plist_path = os.path.join(self.launch_agent_dir, self.plist_filename)
            self.enabled_path = self.plist_path

        elif self.system == "Linux":
            # Linux: 使用 ~/.config/autostart
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
            self.autostart_dir = os.path.join(xdg_config_home, "autostart")
            self.desktop_filename = f"{self.app_name.lower()}.desktop"
            self.desktop_path = os.path.join(self.autostart_dir, self.desktop_filename)
            self.enabled_path = self.desktop_path

        else:
            self.enabled_path = None

    def is_enabled(self):
        """检查是否已开启开机自启"""
        if self.system == "Windows":
            return self._is_enabled_windows()
        elif self.system == "Darwin":
            return self._is_enabled_macos()
        elif self.system == "Linux":
            return self._is_enabled_linux()
        return False

    def _is_enabled_windows(self):
        """检查 Windows 自启动状态"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return value == self.exe_path
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _is_enabled_macos(self):
        """检查 macOS 自启动状态"""
        if not os.path.exists(self.plist_path):
            return False

        try:
            with open(self.plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
                # 检查 ProgramArguments 是否包含我们的路径
                program_args = plist_data.get('ProgramArguments', [])
                return self.exe_path in program_args
        except Exception:
            return False

    def _is_enabled_linux(self):
        """检查 Linux 自启动状态"""
        if not os.path.exists(self.desktop_path):
            return False

        try:
            with open(self.desktop_path, 'r') as f:
                content = f.read()
                return self.exe_path in content
        except Exception:
            return False

    def enable(self):
        """开启开机自启"""
        if self.system == "Windows":
            return self._enable_windows()
        elif self.system == "Darwin":
            return self._enable_macos()
        elif self.system == "Linux":
            return self._enable_linux()
        else:
            print(f"不支持的操作系统: {self.system}")
            return False

    def _enable_windows(self):
        """Windows 开启自启动"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.exe_path)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"开启自启失败: {e}")
            return False

    def _enable_macos(self):
        """macOS 开启自启动 (使用 launchd)"""
        try:
            # 创建 LaunchAgents 目录（如果不存在）
            os.makedirs(self.launch_agent_dir, exist_ok=True)

            # 创建 plist 文件
            plist_data = {
                'Label': f'com.{self.app_name.lower()}',
                'ProgramArguments': [self.exe_path],
                'RunAtLoad': True,
                'KeepAlive': False,
                'StandardOutPath': '/tmp/seatguard.log',
                'StandardErrorPath': '/tmp/seatguard.error.log'
            }

            with open(self.plist_path, 'wb') as f:
                plistlib.dump(plist_data, f)

            # 加载 launchd job
            os.system(f'launchctl load {self.plist_path}')

            return True
        except Exception as e:
            print(f"开启自启失败: {e}")
            return False

    def _enable_linux(self):
        """Linux 开启自启动"""
        try:
            # 创建 autostart 目录（如果不存在）
            os.makedirs(self.autostart_dir, exist_ok=True)

            # 创建 .desktop 文件
            desktop_content = f"""[Desktop Entry]
Type=Application
Name={self.app_name}
Exec={self.exe_path}
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""

            with open(self.desktop_path, 'w') as f:
                f.write(desktop_content)

            return True
        except Exception as e:
            print(f"开启自启失败: {e}")
            return False

    def disable(self):
        """关闭开机自启"""
        if self.system == "Windows":
            return self._disable_windows()
        elif self.system == "Darwin":
            return self._disable_macos()
        elif self.system == "Linux":
            return self._disable_linux()
        else:
            return False

    def _disable_windows(self):
        """Windows 关闭自启动"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return True  # 本来就没有，视为关闭成功
        except Exception as e:
            print(f"关闭自启失败: {e}")
            return False

    def _disable_macos(self):
        """macOS 关闭自启动"""
        try:
            # 先 unload（如果已加载）
            if os.path.exists(self.plist_path):
                os.system(f'launchctl unload {self.plist_path}')

            # 删除 plist 文件
            if os.path.exists(self.plist_path):
                os.remove(self.plist_path)

            return True
        except Exception as e:
            print(f"关闭自启失败: {e}")
            return False

    def _disable_linux(self):
        """Linux 关闭自启动"""
        try:
            if os.path.exists(self.desktop_path):
                os.remove(self.desktop_path)
            return True
        except Exception as e:
            print(f"关闭自启失败: {e}")
            return False
