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