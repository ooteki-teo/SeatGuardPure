"""
SeatGuard 状态机模块
"""

import logging

logger = logging.getLogger(__name__)


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

        # 休息期间重置计数
        self.relax_reset_count = 0  # 休息期间检测到人脸的次数

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
        self.relax_reset_count = 0

    def check_rest_timeout(self, current_time):
        """检查休息是否超时（倒计时作为条件判断工具）"""
        elapsed = current_time - self.rest_start_time
        return elapsed >= self.config.rest_countdown, elapsed

    def check_check_timeout(self, current_time):
        """检查检测用户是否超时"""
        elapsed = current_time - self.check_user_start_time
        return elapsed >= self.config.check_timeout, elapsed

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

    def try_reset_relax_countdown(self, current_time):
        """
        尝试重置休息倒计时

        Returns:
            tuple: (是否允许重置, 是否强制进入CHECK)
        """
        max_resets = self.config.max_relax_resets
        if self.relax_reset_count >= max_resets:
            # 达到最大重置次数，强制进入 CHECK
            return False, True

        # 增加重置计数并重置倒计时
        self.relax_reset_count += 1
        self.rest_start_time = current_time
        return True, False

    def get_relax_remaining_resets(self):
        """获取剩余可重置次数"""
        return max(0, self.config.max_relax_resets - self.relax_reset_count)