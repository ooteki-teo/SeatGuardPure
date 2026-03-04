"""
SeatGuard - 智能久坐提醒系统
主程序入口 - 无GUI版本，使用pystray系统托盘
"""

import sys
import os
import threading
import time
import logging

# 【关键修复】防止 --windowed 模式下 sys.stdout 为 None 导致崩溃
if sys.platform == 'win32' and sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

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
from report_generator import ReportGenerator
from state_machine import SeatGuardStateMachine
from screenshot import ScreenshotCapture
from tray_icon import TrayIconFactory
# 任务管理已迁移到 Web 界面
from api_server import APIServer




class SeatGuardApp:
    """SeatGuard 应用程序主类"""

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

        # 报告生成器
        self.report_generator = ReportGenerator(self.log)

        # API 服务器 (Web UI)
        self.api_server = APIServer(
            self.report_generator,
            self.config,
            host="127.0.0.1",
            port=8765
        )

        # 状态机
        self.is_monitoring = False
        self.running = False
        self.state_machine = SeatGuardStateMachine(self.config)
        self.State = self.state_machine.State  # 引用状态机中的状态枚举

        # 时间记录（倒计时作为条件判断工具）
        self.no_face_start_time = 0     # 连续未检测到人脸的起始时间
        self.last_remind_time = 0       # 控制通知频率的时间戳

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

    def _capture_screenshot(self, frame, prefix="capture"):
        """捕获截图 - 委托给 ScreenshotCapture"""
        ScreenshotCapture.capture_screenshot(frame, self.config, self.log, prefix)

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

            # 重置状态机
            self.state_machine.reset()
            self.no_face_start_time = 0
            self.last_remind_time = 0
            self.notifier.reset()
            self.current_faces = []
            self.timer.reset()
            self.pending_screenshot = None  # 待截图标志 (prefix, frame)

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
                # 获取当前状态
                state = None
                if is_running and hasattr(self, 'state_machine'):
                    state = self.state_machine.state

                new_icon = TrayIconFactory.create_state_icon(state, is_running, self.log)
                if new_icon:
                    self.tray.icon = new_icon
                    state_name = state if state else "未运行"
                    self.log(f"托盘图标已更新: {state_name}")
            except Exception as e:
                self.log(f"更新托盘图标失败: {e}")

    def _create_icon(self, is_running):
        """创建托盘图标（兼容旧版本）"""
        return self._create_tray_icon(is_running)

    def _create_tray_icon(self, is_running):
        """创建托盘图标 - 委托给 TrayIconFactory"""
        return TrayIconFactory.create_tray_icon(is_running, self.log)

    def _get_icon_path(self):
        """获取图标路径 - 委托给 TrayIconFactory"""
        return TrayIconFactory.get_icon_path()

    def _monitor_loop(self):
        """监测主循环 - 每DETECT_INTERVAL检测一次"""
        # 摄像头索引固定为0
        camera_index = 0
        camera_available = True  # 摄像头是否可用
        retry_count = 0
        max_retries = 3

        last_detect_time = 0  # 上次检测时间

        while self.running:
            try:
                current_time = time.time()

                # 到达检测时间
                if current_time - last_detect_time >= self.config.detect_interval:
                    last_detect_time = current_time

                    # 尝试打开摄像头进行检测
                    if camera_available:
                        try:
                            self.camera = Camera(camera_index)
                            self.camera.open()
                            if self.camera.is_opened:
                                self.log("摄像头已开启")
                                # 等待摄像头初始化完成（避免检测到纯黑色图像）
                                time.sleep(2)
                                self._do_detection()
                                # 检测完成后关闭摄像头
                                self.camera.release()
                                self.camera = None
                                self.log("摄像头已关闭")
                            else:
                                raise RuntimeError("无法打开摄像头")
                        except Exception as e:
                            # 减少日志输出
                            pass
                            camera_available = False
                            retry_count += 1
                            # 标记摄像头不可用，视为未检测到人像
                            self._do_detection_no_camera()
                            # 重置计数器，每隔一段时间尝试重新打开
                            if retry_count >= max_retries:
                                # 减少日志输出
                                pass
                    else:
                        # 摄像头不可用时，视为未检测到人像
                        self._do_detection_no_camera()

                # 控制CPU占用
                time.sleep(0.5)

            except Exception as e:
                self.log(f"监测异常: {e}")
                time.sleep(1)

    # ==================== 状态机辅助方法 ====================

    def _check_away_timeout(self, current_time):
        """检查离开是否超时（倒计时作为条件判断工具）"""
        away_duration = 5 * 60  # 5分钟
        if self.no_face_start_time == 0:
            return False, 0
        elapsed = current_time - self.no_face_start_time
        return elapsed >= away_duration, elapsed

    def _on_enter_work(self, current_time):
        """进入工作模式"""
        self.state_machine.user_present_in_work = True
        self.timer.reset()
        self.timer.start()

    def _on_enter_relax(self, current_time):
        """进入休息模式"""
        self.state_machine.rest_start_time = current_time
        self.last_remind_time = 0  # 重置提醒时间

    def _on_enter_away(self, current_time):
        """进入离开模式"""
        self.no_face_start_time = 0  # 重置

    # ==================== 核心检测逻辑 ====================

    def _do_detection(self):
        """执行一次人脸检测 - 状态机控制"""
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

            # 获取配置
            reminder_interval = self.config.rest_reminder_interval
            sm = self.state_machine  # 状态机简写

            # ====== 状态机处理 ======
            state = sm.state

            # --- 检测到人脸 ---
            if face_detected:
                # 重置离开时间
                self.no_face_start_time = 0

                # 先执行待截图（如果有），确保在有人脸时拍照
                if self.pending_screenshot:
                    prefix, pending_frame = self.pending_screenshot
                    self._capture_screenshot(frame, prefix)
                    self.pending_screenshot = None

                if state == self.State.AWAY:
                    # AWAY → WORK: 检测到人脸，回到工作模式（静默恢复，不发通知）
                    result = sm.transition_to(self.State.WORK, current_time, "检测到人脸")
                    if result:
                        self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                        self._update_tray_icon(True)
                    sm.on_enter_work(current_time, self.timer)
                    # 直接截图：进入工作模式（当前帧已有人脸）
                    self._capture_screenshot(frame, "work_start")

                elif state == self.State.WORK:
                    # WORK: 检测到人脸
                    if not sm.user_present_in_work:
                        sm.user_present_in_work = True
                        self.timer.reset()
                        self.timer.start()
                        self.log("检测到落座，开始工作计时")
                        # 直接截图：进入工作模式（当前帧已有人脸）
                        self._capture_screenshot(frame, "work_start")

                    if self.timer.is_time_up():
                        # 久坐超时，提醒后进入休息模式
                        if current_time - self.last_remind_time >= reminder_interval:
                            self.log("久坐超时！请适当休息！")
                            # 设置待截图：工作结束
                            self.pending_screenshot = ("work_end", None)
                            self.last_remind_time = current_time
                            # 状态转换: WORK → RELAX（只有久坐超时才能进入）
                            result = sm.transition_to(self.State.RELAX, current_time, "久坐超时")
                            if result:
                                self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                                self.notifier.notify("状态切换", "久坐超时！请休息一下吧！")
                                self._update_tray_icon(True)
                            sm.on_enter_relax(current_time)
                    else:
                        # 减少日志输出，不每20秒打印
                        pass

                elif state == self.State.RELAX:
                    # RELAX: 休息中检测到人脸
                    can_reset, force_check = sm.try_reset_relax_countdown(current_time)
                    if force_check:
                        # 达到最大重置次数，强制进入 CHECK 模式
                        result = sm.transition_to(self.State.CHECK, current_time, "休息期间多次坐下")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                            self.notifier.notify("状态切换", "休息时间到！请回到座位继续工作！")
                            self._update_tray_icon(True)
                        sm.on_enter_check(current_time)
                    else:
                        # 允许重置倒计时
                        remaining_resets = sm.get_relax_remaining_resets()
                        self.log(f"休息不充分！请继续休息！剩余{remaining_resets}次重置机会")
                        if current_time - self.last_remind_time >= reminder_interval:
                            self.notifier.notify("状态切换", f"休息不充分！请继续休息！剩余{remaining_resets}次机会")
                            self.last_remind_time = current_time

                elif state == self.State.CHECK:
                    # CHECK → WORK: 3分钟内检测到人脸（静默恢复，不发通知）
                    result = sm.transition_to(self.State.WORK, current_time, "检测到人脸")
                    if result:
                        self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                        self._update_tray_icon(True)
                    sm.on_enter_work(current_time, self.timer)
                    # 直接截图：进入工作模式（当前帧已有人脸）
                    self._capture_screenshot(frame, "work_start")

            # --- 未检测到人脸 ---
            else:
                if state == self.State.WORK:
                    # WORK 状态下，用户离开座位时不进入 RELAX
                    # 只记录时间，等待用户回来继续计时，或5分钟无人后进入 AWAY
                    if self.no_face_start_time == 0:
                        self.no_face_start_time = current_time

                    away_time = current_time - self.no_face_start_time

                    # 连续5分钟检测不到人脸 → 进入 AWAY
                    if away_time >= self.config.away_timeout:
                        result = sm.transition_to(self.State.AWAY, current_time, "5分钟无人")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                            # 静默进入 AWAY 模式，不发通知
                            pass
                            self._update_tray_icon(True)
                    else:
                        # 减少日志输出，暂时离开时只在状态变化时输出
                        pass

                elif state == self.State.RELAX:
                    # 检查休息倒计时
                    is_timeout, elapsed = sm.check_rest_timeout(current_time)
                    remaining = self.config.rest_countdown - elapsed

                    if is_timeout:
                        # RELAX → CHECK: 休息满2分钟
                        result = sm.transition_to(self.State.CHECK, current_time, "2分钟倒计时结束")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                            self.notifier.notify("状态切换", "休息时间到！请回到座位继续工作！")
                            self._update_tray_icon(True)
                        sm.on_enter_check(current_time)
                    else:
                        # 减少日志输出
                        pass

                elif state == self.State.CHECK:
                    # 检查检测用户倒计时
                    is_timeout, elapsed = sm.check_check_timeout(current_time)
                    remaining = self.config.check_timeout - elapsed

                    if is_timeout:
                        # CHECK → AWAY: 3分钟超时
                        result = sm.transition_to(self.State.AWAY, current_time, "3分钟无人")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                            # 静默进入 AWAY 模式，不发通知
                            pass
                            self._update_tray_icon(True)
                    else:
                        # 减少日志输出
                        pass

                # AWAY 状态: 静默挂起，不做任何处理

        except Exception as e:
            self.log(f"检测异常: {e}")

    def _do_detection_no_camera(self):
        """摄像头不可用时视为未检测到人像，保持状态机逻辑正常运行"""
        current_time = time.time()
        sm = self.state_machine  # 状态机简写
        state = sm.state

        # 视为未检测到人脸
        face_detected = False

        # --- 未检测到人脸 ---
        if state == self.State.WORK:
            # WORK 状态下，用户离开座位时不进入 RELAX
            # 只记录时间，等待用户回来继续计时，或5分钟无人后进入 AWAY
            if self.no_face_start_time == 0:
                self.no_face_start_time = current_time

            away_time = current_time - self.no_face_start_time

            # 连续5分钟检测不到人脸 → 进入 AWAY
            if away_time >= self.config.away_timeout:
                result = sm.transition_to(self.State.AWAY, current_time, "5分钟无人")
                if result:
                    self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    self.notifier.notify("状态切换", "您已离开座位 5 分钟，进入离开模式")
                    self._update_tray_icon(True)
            else:
                if sm.user_present_in_work:
                    remaining = self.timer.format_time(self.timer.get_remaining_seconds())
                    # 减少日志输出
                    pass
                else:
                    # 减少日志输出
                    pass

        elif state == self.State.RELAX:
            # 检查休息倒计时
            is_timeout, elapsed = sm.check_rest_timeout(current_time)
            remaining = self.config.rest_countdown - elapsed

            if is_timeout:
                # RELAX → CHECK: 休息满2分钟
                result = sm.transition_to(self.State.CHECK, current_time, "2分钟倒计时结束")
                if result:
                    self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    self.notifier.notify("状态切换", "休息时间到！请回到座位继续工作！")
                    self._update_tray_icon(True)
                sm.on_enter_check(current_time)
            else:
                # 减少日志输出
                pass

        elif state == self.State.CHECK:
            # 检查检测用户倒计时
            is_timeout, elapsed = sm.check_check_timeout(current_time)
            remaining = self.config.check_timeout - elapsed

            if is_timeout:
                # CHECK → AWAY: 3分钟超时
                result = sm.transition_to(self.State.AWAY, current_time, "3分钟无人")
                if result:
                    self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    self.notifier.notify("状态切换", "您已离开座位，进入离开模式")
                    self._update_tray_icon(True)
            else:
                # 减少日志输出
                pass

        # AWAY 状态: 静默挂起，不做任何处理

    def run(self):
        """运行应用程序（启动托盘）"""
        self.log("正在启动系统托盘...")

        # 启动 API 服务器
        self.log("启动 Web API 服务器...")
        self.api_server.start(open_browser=False)
        self.log(f"Web 控制面板已启动: {self.api_server.get_url()}")

        # 先初始化托盘
        self._setup_tray()

        # 启动后自动开始监测
        self.log("自动启动监测...")
        self.start_monitoring()

        if self.tray:
            self.log("SeatGuard 已启动（系统托盘模式）")
            self.log(f"提醒时长: {self.config.reminder_duration} 分钟")
            self.log(f"休息宽限期: {self.config.grace_period} 秒")
            self.log(f"Web 控制面板: {self.api_server.get_url()}")

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

            self.log("开始创建系统托盘...")

            # 创建图标 - 使用 TrayIconFactory（未运行状态）
            self.log("正在创建托盘图标...")
            icon_image = TrayIconFactory.create_state_icon(None, False, self.log)
            if icon_image is None:
                self.log("图标创建失败，使用默认图标")
                icon_image = TrayIconFactory.create_default_icon()
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
                pystray.MenuItem(
                    "启用截图",
                    self._toggle_screenshot,
                    checked=lambda item: self.config.screenshot_enabled
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(lambda item: self._get_status_text(), self._show_status),
                pystray.Menu.SEPARATOR,
                # Web 界面菜单
                pystray.MenuItem("🌐 打开控制面板", self._trigger_open_main),
                pystray.MenuItem("⚙️ 设置", self._trigger_open_settings),
                pystray.MenuItem("📝 日志", self._trigger_open_logs),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("📊 今日日报", self._trigger_open_reports),
                pystray.MenuItem("📈 本周周报", self._trigger_open_reports),
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

    def _toggle_screenshot(self, icon=None, item=None):
        """切换截图功能"""
        self.config.screenshot_enabled = not self.config.screenshot_enabled
        if self.config.screenshot_enabled:
            self.log("已开启截图功能")
            self.notifier.notify("设置已更改", "截图功能已开启。\n工作开始/结束时将自动截图。")
        else:
            self.log("已关闭截图功能")
            self.notifier.notify("设置已更改", "截图功能已关闭。")

    def _trigger_open_settings(self, icon=None, item=None):
        """打开设置页面"""
        self.api_server.open_browser("/settings")

    def _trigger_open_logs(self, icon=None, item=None):
        """打开日志页面"""
        self.api_server.open_browser("/logs")

    def _trigger_open_reports(self, icon=None, item=None):
        """打开报告页面"""
        self.api_server.open_browser("/reports")

    def _trigger_open_main(self, icon=None, item=None):
        """打开主页"""
        self.api_server.open_browser("/")

    def _get_status_text(self):
        """获取当前状态文本（用于托盘菜单显示）"""
        if not self.is_monitoring:
            return "不在监测"
        sm = self.state_machine
        state = sm.state
        current_time = time.time()

        if state == self.State.AWAY:
            return "离开模式"
        elif state == self.State.CHECK:
            elapsed = current_time - sm.check_user_start_time
            remaining = self.config.check_timeout - elapsed
            return f"等待模式 ({int(remaining)}秒)"
        elif state == self.State.RELAX:
            elapsed = current_time - sm.rest_start_time
            remaining = self.config.rest_countdown - elapsed
            if remaining < 0:
                remaining = 0
            return f"休息模式 ({int(remaining)}秒)"
        elif state == self.State.WORK:
            return "工作模式"
        else:
            return "未知状态"

    def _show_status(self, icon=None, item=None):
        """显示状态"""
        if not self.is_monitoring:
            status = "未运行"
        else:
            sm = self.state_machine
            state = sm.state
            current_time = time.time()

            if state == self.State.AWAY:
                status = "离开模式 (away)"
            elif state == self.State.CHECK:
                elapsed = current_time - sm.check_user_start_time
                remaining = self.config.check_timeout - elapsed
                status = f"检测用户中 - 剩余: {int(remaining)}秒"
            elif state == self.State.RELAX:
                elapsed = current_time - sm.rest_start_time
                remaining = self.config.rest_countdown - elapsed
                if remaining < 0:
                    remaining = 0
                status = f"休息模式 (relax) - 剩余: {int(remaining)}秒"
            elif state == self.State.WORK:
                remaining = self.timer.get_remaining_seconds()
                seated_seconds = self.config.reminder_duration * 60 - remaining
                seated_text = self.timer.format_time(seated_seconds)
                status = f"工作模式 (work) - 已坐: {seated_text}"
            else:
                status = "未知状态"

        self.notifier.notify("SeatGuard 状态", status)

    def _show_daily_report(self, icon=None, item=None):
        """显示今日日报"""
        report = self.report_generator.generate_daily_report()
        # 将报告内容按行分割，用通知显示
        lines = report.split("\n")
        # 通知消息限制长度，取中间部分
        if len(lines) > 6:
            display_lines = lines[2:8]  # 显示中间部分
            message = "\n".join(display_lines) + "\n..."
        else:
            message = report

        self.notifier.notify("📊 今日日报", message)

    def _show_weekly_report(self, icon=None, item=None):
        """显示本周周报"""
        report = self.report_generator.generate_weekly_report()
        lines = report.split("\n")
        if len(lines) > 6:
            display_lines = lines[2:8]
            message = "\n".join(display_lines) + "\n..."
        else:
            message = report

        self.notifier.notify("📈 本周周报", message)

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
    import multiprocessing
    multiprocessing.freeze_support()  # 防止打包后的 exe 出现进程无限嵌套重启的问题
    main()
