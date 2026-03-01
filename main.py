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


# ==================== 状态机类 ====================
class SeatGuardStateMachine:
    """SeatGuard 状态机"""

    # 定义状态
    class State:
        WORK = "work"       # 工作模式
        RELAX = "relax"     # 休息模式（久坐超时后）
        CHECK = "check"    # 检测用户模式
        AWAY = "away"      # 离开模式

    def __init__(self, config):
        self.config = config
        self.current_state = self.State.WORK

        # 辅助标志
        self.user_present_in_work = False  # 工作期间是否已落座

        # 时间记录
        self.rest_start_time = 0       # 休息模式开始时间
        self.check_user_start_time = 0  # 检测用户模式开始时间

    @property
    def state(self):
        return self.current_state

    def is_work(self):
        return self.current_state == self.State.WORK

    def is_relax(self):
        return self.current_state == self.State.RELAX

    def is_check(self):
        return self.current_state == self.State.CHECK

    def is_away(self):
        return self.current_state == self.State.AWAY

    def reset(self):
        """重置状态机"""
        self.current_state = self.State.WORK
        self.user_present_in_work = False
        self.rest_start_time = 0
        self.check_user_start_time = 0

    def check_rest_timeout(self, current_time):
        """检查休息是否超时（倒计时作为条件判断工具）"""
        elapsed = current_time - self.rest_start_time
        return elapsed >= self.config.rest_countdown, elapsed

    def check_check_timeout(self, current_time):
        """检查检测用户是否超时"""
        elapsed = current_time - self.check_user_start_time
        return elapsed >= 3 * 60, elapsed  # 3分钟

    def transition_to(self, new_state, current_time, reason=""):
        """状态转换"""
        old_state = self.current_state
        if old_state == new_state:
            return False

        self.current_state = new_state
        return old_state, new_state, reason

    def on_enter_work(self, current_time, timer):
        """进入工作模式"""
        timer.reset()
        timer.start()
        self.user_present_in_work = True

    def on_enter_relax(self, current_time):
        """进入休息模式"""
        self.rest_start_time = current_time

    def on_enter_check(self, current_time):
        """进入检测用户模式"""
        self.check_user_start_time = current_time

    def on_enter_away(self, current_time):
        """进入离开模式"""
        pass


class SeatGuardApp:
    """SeatGuard 应用程序主类"""

    # 检测参数
    DETECT_INTERVAL = 15.0          # 每15秒检测一次

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
        """
        捕获截图并保存到日志目录

        Args:
            frame: 摄像头帧
            prefix: 文件名前缀
        """
        # 检查截图功能是否启用
        if not self.config.screenshot_enabled:
            return

        try:
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont

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
                self.log(f"截图已保存: {filename}")
        except Exception as e:
            self.log(f"截图失败: {e}")

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
                if current_time - last_detect_time >= self.DETECT_INTERVAL:
                    last_detect_time = current_time

                    # 尝试打开摄像头进行检测
                    if camera_available:
                        try:
                            self.camera = Camera(camera_index)
                            self.camera.open()
                            if self.camera.is_opened:
                                self.log("摄像头已开启")
                                self._do_detection()
                                # 检测完成后关闭摄像头
                                self.camera.release()
                                self.camera = None
                                self.log("摄像头已关闭")
                            else:
                                raise RuntimeError("无法打开摄像头")
                        except Exception as e:
                            self.log(f"摄像头不可用: {e}，视为无人在座")
                            camera_available = False
                            retry_count += 1
                            # 标记摄像头不可用，视为未检测到人像
                            self._do_detection_no_camera()
                            # 重置计数器，每隔一段时间尝试重新打开
                            if retry_count >= max_retries:
                                self.log(f"连续{max_retries}次摄像头不可用，暂停尝试")
                    else:
                        # 摄像头不可用时，视为未检测到人像
                        self._do_detection_no_camera()

                # 控制CPU占用
                time.sleep(0.5)

            except Exception as e:
                self.log(f"监测异常: {e}")
                time.sleep(1)

    # ==================== 状态机辅助方法 ====================

    def _check_rest_timeout(self, current_time):
        """检查休息是否超时（倒计时作为条件判断工具）"""
        rest_duration = self.config.rest_countdown
        elapsed = current_time - self.rest_start_time
        return elapsed >= rest_duration, elapsed

    def _check_check_timeout(self, current_time):
        """检查检测用户是否超时（倒计时作为条件判断工具）"""
        check_duration = 3 * 60  # 3分钟
        elapsed = current_time - self.check_user_start_time
        return elapsed >= check_duration, elapsed

    def _check_away_timeout(self, current_time):
        """检查离开是否超时（倒计时作为条件判断工具）"""
        away_duration = 5 * 60  # 5分钟
        if self.no_face_start_time == 0:
            return False, 0
        elapsed = current_time - self.no_face_start_time
        return elapsed >= away_duration, elapsed

    def _transition_to(self, new_state, current_time, reason=""):
        """状态转换"""
        old_state = self.current_state
        if old_state == new_state:
            return False

        self.current_state = new_state
        self.log(f"状态转换: {old_state} → {new_state} ({reason})")
        return True

    def _on_enter_work(self, current_time):
        """进入工作模式"""
        self.timer.reset()
        self.timer.start()
        self.user_present_in_work = True

    def _on_enter_relax(self, current_time):
        """进入休息模式"""
        self.rest_start_time = current_time
        self.last_remind_time = 0  # 重置提醒时间

    def _on_enter_check(self, current_time):
        """进入检测用户模式"""
        self.check_user_start_time = current_time

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

                if state == self.State.AWAY:
                    # AWAY → WORK: 检测到人脸，回到工作模式
                    result = sm.transition_to(self.State.WORK, current_time, "检测到人脸")
                    if result:
                        self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    sm.on_enter_work(current_time, self.timer)

                elif state == self.State.WORK:
                    # WORK: 检测到人脸
                    if not sm.user_present_in_work:
                        sm.user_present_in_work = True
                        self.timer.reset()
                        self.timer.start()
                        self.log("检测到落座，开始工作计时")
                        # 截图：进入工作模式
                        self._capture_screenshot(frame, "work_start")

                    if self.timer.is_time_up():
                        # 久坐超时，提醒后进入休息模式
                        if current_time - self.last_remind_time >= reminder_interval:
                            self.log("久坐提醒！请适当休息！起来走走！")
                            # 截图：工作结束
                            self._capture_screenshot(frame, "work_end")
                            self.notifier.notify(
                                title="救命啊，你坐太久了吧",
                                message=f"您已坐着超过 {self.config.reminder_duration} 分钟，请适当休息！\n\"想要活得久，喝杯水！站起来！\""
                            )
                            self.last_remind_time = current_time
                            # 状态转换: WORK → RELAX（只有久坐超时才能进入）
                            result = sm.transition_to(self.State.RELAX, current_time, "久坐超时")
                            if result:
                                self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                            sm.on_enter_relax(current_time)
                    else:
                        remaining = self.timer.format_time(self.timer.get_remaining_seconds())
                        self.log(f"工作计时中: {remaining}")

                elif state == self.State.RELAX:
                    # RELAX: 休息中检测到人脸，重置倒计时
                    sm.rest_start_time = current_time
                    self.log("休息中断，重置倒计时")

                    if current_time - self.last_remind_time >= reminder_interval:
                        self.notifier.notify(
                            title="休息不充分",
                            message="休息时间不够，请离开座位活动一下！"
                        )
                        self.last_remind_time = current_time

                elif state == self.State.CHECK:
                    # CHECK → WORK: 3分钟内检测到人脸
                    result = sm.transition_to(self.State.WORK, current_time, "检测到人脸")
                    if result:
                        self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    sm.on_enter_work(current_time, self.timer)

            # --- 未检测到人脸 ---
            else:
                if state == self.State.WORK:
                    # WORK 状态下，用户离开座位时不进入 RELAX
                    # 只记录时间，等待用户回来继续计时，或5分钟无人后进入 AWAY
                    if self.no_face_start_time == 0:
                        self.no_face_start_time = current_time

                    away_time = current_time - self.no_face_start_time

                    # 连续5分钟检测不到人脸 → 进入 AWAY
                    if away_time >= 5 * 60:
                        result = sm.transition_to(self.State.AWAY, current_time, "5分钟无人")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    else:
                        if sm.user_present_in_work:
                            remaining = self.timer.format_time(self.timer.get_remaining_seconds())
                            self.log(f"暂时离开，工作计时继续: {remaining}")
                        else:
                            self.log(f"等待落座... (已离开 {int(away_time)}秒)")

                elif state == self.State.RELAX:
                    # 检查休息倒计时
                    is_timeout, elapsed = sm.check_rest_timeout(current_time)
                    remaining = self.config.rest_countdown - elapsed

                    if is_timeout:
                        # RELAX → CHECK: 休息满2分钟
                        result = sm.transition_to(self.State.CHECK, current_time, "2分钟倒计时结束")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                        sm.on_enter_check(current_time)
                    else:
                        self.log(f"休息中，剩余 {int(remaining)}秒")

                elif state == self.State.CHECK:
                    # 检查检测用户倒计时
                    is_timeout, elapsed = sm.check_check_timeout(current_time)
                    remaining = (3 * 60) - elapsed

                    if is_timeout:
                        # CHECK → AWAY: 3分钟超时
                        result = sm.transition_to(self.State.AWAY, current_time, "3分钟无人")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    else:
                        self.log(f"检测用户中，剩余 {int(remaining)}秒")

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
            if away_time >= 5 * 60:
                result = sm.transition_to(self.State.AWAY, current_time, "5分钟无人")
                if result:
                    self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
            else:
                if sm.user_present_in_work:
                    remaining = self.timer.format_time(self.timer.get_remaining_seconds())
                    self.log(f"暂时离开(摄像头不可用)，工作计时继续: {remaining}")
                else:
                    self.log(f"等待落座(摄像头不可用)... (已离开 {int(away_time)}秒)")

        elif state == self.State.RELAX:
            # 检查休息倒计时
            is_timeout, elapsed = sm.check_rest_timeout(current_time)
            remaining = self.config.rest_countdown - elapsed

            if is_timeout:
                # RELAX → CHECK: 休息满2分钟
                result = sm.transition_to(self.State.CHECK, current_time, "2分钟倒计时结束")
                if result:
                    self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                sm.on_enter_check(current_time)
            else:
                self.log(f"休息中(摄像头不可用)，剩余 {int(remaining)}秒")

        elif state == self.State.CHECK:
            # 检查检测用户倒计时
            is_timeout, elapsed = sm.check_check_timeout(current_time)
            remaining = (3 * 60) - elapsed

            if is_timeout:
                # CHECK → AWAY: 3分钟超时
                result = sm.transition_to(self.State.AWAY, current_time, "3分钟无人")
                if result:
                    self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
            else:
                self.log(f"检测用户中(摄像头不可用)，剩余 {int(remaining)}秒")

        # AWAY 状态: 静默挂起，不做任何处理

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
                pystray.MenuItem(
                    "启用截图",
                    self._toggle_screenshot,
                    checked=lambda item: self.config.screenshot_enabled
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

    def _toggle_screenshot(self, icon=None, item=None):
        """切换截图功能"""
        self.config.screenshot_enabled = not self.config.screenshot_enabled
        if self.config.screenshot_enabled:
            self.log("已开启截图功能")
            self.notifier.notify("设置已更改", "截图功能已开启。\n工作开始/结束时将自动截图。")
        else:
            self.log("已关闭截图功能")
            self.notifier.notify("设置已更改", "截图功能已关闭。")

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
                remaining = (3 * 60) - elapsed
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
