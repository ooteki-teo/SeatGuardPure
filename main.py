"""
SeatGuard - 智能久坐提醒系统
主程序入口 - 无GUI版本，使用pystray系统托盘
"""

import sys
import os
import threading
import time
import cv2
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
def setup_logging():
    """配置日志到文件"""
    log_dir = os.path.dirname(os.path.abspath(__file__))
    # PyInstaller 打包后的路径
    if hasattr(sys, '_MEIPASS'):
        log_dir = os.path.dirname(sys.executable)

    log_file = os.path.join(log_dir, 'seat_guard.log')

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"日志文件: {log_file}")

setup_logging()

from config import Config
from detector import FaceDetector, Camera
from timer import SeatTimer
from notifier import Notifier
from autostart import AutoStartManager


class SeatGuardApp:
    """SeatGuard 应用程序主类"""

    # 检测参数
    DETECT_INTERVAL = 1.0          # 每秒检测一次

    def __init__(self):
        self.config = Config()

        # 检测模块
        self.face_detector = None
        self.camera = None

        # 计时器
        self.timer = SeatTimer(self.config.reminder_duration)

        # 提醒器 - 传入日志回调
        self.notifier = Notifier(self.log)

        # 自启管理器
        self.autostart = AutoStartManager()

        # 状态变量 - 四态状态机
        self.is_monitoring = False
        self.running = False

        # 四态状态:
        # - is_work: 工作模式（正常计时）
        # - is_relax: 休息模式（2分钟倒计时）
        # - check_user: 检测用户状态（休息结束后检测3分钟）
        # - is_not_here: 离开模式（连续5分钟无人，暂停提醒）
        self.is_work = True
        self.is_relax = False
        self.check_user = False
        self.is_not_here = False

        # 辅助标志
        self.user_present_in_work = False  # 工作期间是否已落座

        # 时间记录
        self.no_face_start_time = 0     # 连续未检测到人脸的起始时间
        self.rest_start_time = 0       # 休息模式倒计时的起始时间
        self.last_remind_time = 0       # 控制通知频率的时间戳
        self.check_user_start_time = 0  # 检测用户状态的起始时间

        # 监测线程
        self.monitor_thread = None

        # 当前检测到的人脸
        self.current_faces = []

        # 系统托盘
        self.tray = None

        # 日志消息回调
        self.log_callback = None

    def set_log_callback(self, callback):
        """设置日志回调函数"""
        self.log_callback = callback

    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)
        # 使用 try-except 防止在 console=False 时崩溃
        try:
            print(f"[SeatGuard] {message}")
        except Exception:
            pass
        logging.info(message)

    def start_monitoring(self):
        """启动监测"""
        if self.is_monitoring:
            return

        try:
            # 初始化人脸检测器
            self.face_detector = FaceDetector()
            self.log("人脸检测器初始化成功")

            # 初始化计时器（默认40分钟）
            self.timer = SeatTimer(self.config.reminder_duration)

            # 重置状态
            self.is_work = True
            self.is_relax = False
            self.check_user = False
            self.is_not_here = False
            self.user_present_in_work = False
            self.no_face_start_time = 0
            self.rest_start_time = 0
            self.last_remind_time = 0
            self.check_user_start_time = 0
            self.notifier.reset()
            self.current_faces = []
            self.timer.reset()

            # 设置运行状态
            self.is_monitoring = True
            self.running = True

            self.log("开始监测")

            # 启动监测线程
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

            # 更新托盘图标
            self._update_tray_icon(True)

        except Exception as e:
            self.log(f"启动失败: {e}")
            self.stop_monitoring()

    def stop_monitoring(self):
        """停止监测"""
        self.running = False
        self.is_monitoring = False

        # 释放摄像头
        if self.camera:
            self.camera.release()
            self.camera = None

        self.log("监测已停止")

        # 更新托盘图标
        self._update_tray_icon(False)

    def _update_tray_icon(self, is_running):
        """更新托盘图标状态"""
        if self.tray:
            try:
                new_icon = self._create_tray_icon(is_running)
                if new_icon:
                    self.tray.icon = new_icon
                    self.log(f"托盘图标已更新: {'运行中' if is_running else '未运行'}")
            except Exception as e:
                self.log(f"更新托盘图标失败: {e}")

    def _create_icon(self, is_running):
        """创建托盘图标（兼容旧版本）"""
        return self._create_tray_icon(is_running)

    def _create_tray_icon(self, is_running):
        """创建托盘图标"""
        try:
            from PIL import Image, ImageDraw

            # 尝试加载 icon.ico 文件
            icon_path = self._get_icon_path()
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
            self.log(f"创建图标失败: {e}")
            return None

    def _get_icon_path(self):
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

    def _monitor_loop(self):
        """监测主循环 - 每秒检测一次"""
        # 摄像头索引固定为0
        camera_index = 0

        # 持续开启摄像头
        camera_opened = False
        retry_count = 0
        max_retries = 3

        last_detect_time = 0  # 上次检测时间
        sit_threshold = 3    # 坐下确认阈值（连续3次检测到人脸）

        while self.running:
            try:
                current_time = time.time()

                # 动态读取休息时间配置
                grace_period = self.config.grace_period

                # 确保摄像头已打开
                if not camera_opened:
                    try:
                        if self.camera is None:
                            self.camera = Camera(camera_index)
                        if not self.camera.is_opened:
                            self.camera.open()
                        camera_opened = self.camera.is_opened
                        if camera_opened:
                            self.log("摄像头已开启")
                    except Exception as e:
                        self.log(f"打开摄像头失败: {e}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            self.log("无法连接摄像头，停止监测")
                            break
                        time.sleep(1)
                        continue

                # 每秒检测一次
                if current_time - last_detect_time >= self.DETECT_INTERVAL:
                    last_detect_time = current_time
                    self._do_detection()

                # 控制CPU占用
                time.sleep(0.1)

            except Exception as e:
                self.log(f"监测异常: {e}")
                camera_opened = False
                time.sleep(0.5)

        # 清理
        if self.camera:
            self.camera.release()
            self.camera = None

    def _do_detection(self):
        """执行一次人脸检测 - 四态状态机"""
        if not self.camera or not self.camera.is_opened:
            return

        try:
            # 读取摄像头帧
            ret, frame = self.camera.read()
            if not ret or frame is None:
                return

            # 人脸检测
            faces = self.face_detector.detect_faces(frame)
            self.current_faces = faces
            face_detected = len(faces) > 0
            current_time = time.time()

            # 动态读取配置
            rest_duration_sec = self.config.rest_countdown  # 休息倒计时（默认120秒）
            rest_reminder_interval = self.config.rest_reminder_interval  # 提醒间隔（默认20秒）
            not_here_threshold = 5 * 60  # 连续5分钟检测不到人脸
            check_user_threshold = 3 * 60  # 检测用户状态超时3分钟

            # ====== 检测到人脸 ======
            if face_detected:
                # 只要检测到人脸，立即重置"离开"时间计数
                if self.no_face_start_time != 0:
                    self.no_face_start_time = 0

                # 退出 is_not_here 状态，进入工作模式
                if self.is_not_here:
                    self.is_not_here = False
                    self.is_work = True
                    self.user_present_in_work = True
                    self.timer.reset()
                    self.timer.start()
                    self.log("is_not_here=False | 检测到人脸，结束离开状态，重新开始工作计时")

                # 处理各状态下的检测到人脸情况
                if self.is_work:
                    # --- 工作模式 ---
                    if not self.user_present_in_work:
                        self.user_present_in_work = True
                        self.timer.reset()
                        self.timer.start()
                        self.log("is_work=True | 检测到落座，开始工作倒计时")

                    remaining = self.timer.get_remaining_seconds()
                    timer_text = self.timer.format_time(remaining)

                    if self.timer.is_time_up():
                        # 到了预设提醒时间，提醒后进入休息模式
                        if current_time - self.last_remind_time >= rest_reminder_interval:
                            self.log("久坐提醒！请适当休息！起来走走！")
                            self.notifier.notify(
                                title="救命啊，你坐太久了吧",
                                message=f"您已坐着超过 {self.config.reminder_duration} 分钟，请适当休息！\n\"想要活得久，喝杯水！站起来！\""
                            )
                            self.last_remind_time = current_time
                            # 提醒后进入休息模式
                            self.is_work = False
                            self.is_relax = True
                            self.rest_start_time = current_time
                            self.log("久坐提醒后 | 进入休息模式 is_relax=True")
                    else:
                        self.log(f"is_work=True | 工作计时中: {timer_text}")

                elif self.is_relax:
                    # --- 休息模式 ---
                    # 只要在休息模式中检测到人脸，就重新开始2分钟休息时间倒计时
                    self.rest_start_time = current_time
                    self.log("is_relax=True | 休息中断！检测到人脸，重新开始休息倒计时")

                    if current_time - self.last_remind_time >= rest_reminder_interval:
                        self.notifier.notify(
                            title="休息不充分",
                            message="休息时间不够，请离开座位活动一下！"
                        )
                        self.last_remind_time = current_time

                elif self.check_user:
                    # --- 检测用户状态 ---
                    # 3分钟内检测到人脸，回到工作模式
                    self.check_user = False
                    self.is_work = True
                    self.user_present_in_work = True
                    self.timer.reset()
                    self.timer.start()
                    self.log("check_user=False | 检测到人脸，回到工作模式 is_work=True")

            # ====== 未检测到人脸 ======
            else:
                # 记录离开开始时间（只在工作模式时记录）
                if self.is_work and self.no_face_start_time == 0:
                    self.no_face_start_time = current_time

                if self.is_work:
                    # --- 工作模式 ---
                    away_time = current_time - self.no_face_start_time if self.no_face_start_time > 0 else 0

                    # 连续5分钟检测不到人脸 → 进入离开模式
                    if away_time >= not_here_threshold:
                        self.is_not_here = True
                        self.is_work = False
                        self.no_face_start_time = 0  # 重置计时
                        self.log("is_not_here=True | 工作模式下连续5分钟未检测到人脸，进入离开状态")
                    else:
                        # 还不到5分钟，检查是否离开座位
                        if self.user_present_in_work:
                            # 刚离开座位，进入休息模式
                            self.is_work = False
                            self.is_relax = True
                            self.rest_start_time = current_time
                            self.no_face_start_time = 0  # 重置计时
                            self.log("离开座位 | 进入休息模式 is_relax=True")
                        else:
                            self.log(f"is_work=True | 等待落座... (已离开 {int(away_time)} 秒)")

                elif self.is_relax:
                    # --- 休息模式 ---
                    # 休息模式不检测5分钟离开，只计算倒计时
                    rest_time = current_time - self.rest_start_time
                    remaining_rest = rest_duration_sec - rest_time

                    if remaining_rest <= 0:
                        # 休息满2分钟，进入检测用户状态
                        self.is_relax = False
                        self.check_user = True
                        self.check_user_start_time = current_time
                        self.log("休息满2分钟 | 进入检测用户状态 check_user=True")
                    else:
                        self.log(f"is_relax=True | 休息中，剩余: {int(remaining_rest)} 秒")

                elif self.check_user:
                    # --- 检测用户状态 ---
                    # 检测用户状态不检测5分钟离开，只计算3分钟超时
                    check_time = current_time - self.check_user_start_time

                    if check_time >= check_user_threshold:
                        # 3分钟都无人，进入离开模式
                        self.check_user = False
                        self.is_not_here = True
                        self.log("check_user超时3分钟 | 进入离开模式 is_not_here=True")
                    else:
                        remaining_check = check_user_threshold - check_time
                        self.log(f"check_user=True | 检测用户中，剩余: {int(remaining_check)} 秒")

                # is_not_here 状态：静默挂起，不做任何处理

        except Exception as e:
            self.log(f"检测异常: {e}")

    def run(self):
        """运行应用程序（启动托盘）"""
        self.log("正在启动系统托盘...")

        # 先初始化托盘
        self._setup_tray()

        if self.tray:
            self.log("SeatGuard 已启动（系统托盘模式）")
            self.log(f"提醒时长: {self.config.reminder_duration} 分钟")
            self.log(f"休息宽限期: {self.config.grace_period} 秒")
            self.log("点击托盘图标开始/停止监测")

            # 在主线程中运行托盘（会阻塞）
            try:
                self.tray.run()
            except Exception as e:
                self.log(f"托盘异常: {e}")
        else:
            self.log("警告：托盘创建失败，程序将以控制台模式运行")
            self._run_console_mode()

    def _setup_tray(self):
        """设置系统托盘"""
        try:
            import pystray
            from PIL import Image, ImageDraw

            self.log("开始创建系统托盘...")

            # 创建图标 - 创建一个更可靠的图标
            self.log("正在创建托盘图标...")
            icon_image = self._create_tray_icon(False)
            if icon_image is None:
                self.log("图标创建失败，使用默认图标")
                # 创建默认图标（使用 RGBA 格式，pystray 更稳定）
                icon_image = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
                draw = ImageDraw.Draw(icon_image)
                draw.ellipse([8, 8, 56, 56], fill='#95A5A6', outline='#7F8C8D', width=2)
            else:
                self.log(f"图标创建成功: {icon_image.size}, mode={icon_image.mode}")

            # 创建托盘菜单
            self.log("创建托盘菜单...")
            menu = pystray.Menu(
                pystray.MenuItem("开始/停止监测", self._toggle_monitoring),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "开机自动启动",
                    self._toggle_autostart,
                    checked=lambda item: self.autostart.is_enabled()
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("查看状态", self._show_status),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._quit)
            )

            # 创建托盘图标
            self.log("创建 pystray.Icon...")
            self.tray = pystray.Icon(
                "SeatGuard",
                icon_image,
                "SeatGuard - 久坐提醒",
                menu
            )
            self.log("pystray.Icon 创建成功")

            # 不在这里启动托盘，让 run() 方法在主线程中阻塞运行
            self.log("系统托盘已创建")

        except Exception as e:
            self.log(f"创建系统托盘失败: {e}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            self.tray = None

    def _run_tray(self):
        """运行托盘图标"""
        try:
            if self.tray:
                self.tray.run()
        except Exception as e:
            self.log(f"托盘线程异常: {e}")

    def _toggle_monitoring(self, icon=None, item=None):
        """切换监测状态"""
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def _toggle_autostart(self, icon=None, item=None):
        """切换开机自启状态"""
        if self.autostart.is_enabled():
            if self.autostart.disable():
                self.log("已关闭开机自启")
                self.notifier.notify("设置已更改", "SeatGuard 已取消开机自动启动。")
        else:
            if self.autostart.enable():
                self.log("已开启开机自启")
                self.notifier.notify("设置已更改", "SeatGuard 已设置为开机自动启动。")

    def _show_status(self, icon=None, item=None):
        """显示状态"""
        if not self.is_monitoring:
            status = "未运行"
        elif self.is_not_here:
            status = "离开模式 (is_not_here)"
        elif self.check_user:
            status = "检测用户中 (check_user)"
        elif self.is_relax:
            # 计算休息剩余时间
            current_time = time.time()
            rest_time = current_time - self.rest_start_time
            remaining = self.config.rest_countdown - rest_time
            if remaining < 0:
                remaining = 0
            status = f"休息模式 (is_relax) - 剩余: {int(remaining)}秒"
        elif self.is_work:
            remaining = self.timer.get_remaining_seconds()
            seated_seconds = self.config.reminder_duration * 60 - remaining
            seated_text = self.timer.format_time(seated_seconds)
            status = f"工作模式 (is_work) - 已坐: {seated_text}"
        else:
            status = "未知状态"

        self.notifier.notify("SeatGuard 状态", status)

    def _quit(self, icon=None, item=None):
        """退出程序"""
        self.stop_monitoring()
        # pystray 会自动停止，不需要手动调用
        import os
        os._exit(0)

    def _run_console_mode(self):
        """控制台模式运行（备用）"""
        self.log("使用控制台模式...")
        self.start_monitoring()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_monitoring()
            self.log("程序已退出")


def main():
    """主函数"""
    app = SeatGuardApp()
    app.run()


if __name__ == "__main__":
    main()
