"""
计时器模块
"""

import time


class SeatTimer:
    """座位计时器"""

    def __init__(self, duration_minutes=40):
        """
        初始化计时器

        Args:
            duration_minutes: 提醒时长（分钟）
        """
        self.duration_seconds = duration_minutes * 60
        self.start_time = None
        self.elapsed_time = 0
        self.is_running = False
        self.is_paused = False
        self.last_check_time = None

    def start(self):
        """开始计时"""
        self.start_time = time.monotonic()
        self.is_running = True
        self.is_paused = False

    def reset(self):
        """重置计时器"""
        self.start_time = None
        self.elapsed_time = 0
        self.is_running = False
        self.is_paused = False
        self.last_check_time = None

    def pause(self):
        """暂停计时"""
        if self.is_running and not self.is_paused:
            self.elapsed_time += time.monotonic() - self.start_time
            self.is_paused = True

    def resume(self):
        """恢复计时"""
        if self.is_paused:
            self.start_time = time.monotonic()
            self.is_paused = False

    def get_elapsed_seconds(self):
        """
        获取已过时间（秒）

        Returns:
            float: 已过时间
        """
        if not self.is_running:
            return 0

        if self.is_paused:
            return self.elapsed_time

        current = time.monotonic()
        return self.elapsed_time + (current - self.start_time)

    def get_remaining_seconds(self):
        """
        获取剩余时间（秒）

        Returns:
            float: 剩余时间，负数表示已超时
        """
        elapsed = self.get_elapsed_seconds()
        return self.duration_seconds - elapsed

    def is_time_up(self):
        """
        检查是否时间已到

        Returns:
            bool: 是否到达预设时长
        """
        return self.get_remaining_seconds() <= 0

    def set_duration(self, minutes):
        """
        设置提醒时长

        Args:
            minutes: 时长（分钟）
        """
        self.duration_seconds = minutes * 60

    def get_duration(self):
        """获取提醒时长（分钟）"""
        return self.duration_seconds // 60

    def format_time(self, seconds):
        """
        格式化时间显示

        Args:
            seconds: 秒数

        Returns:
            str: 格式化后的时间字符串
        """
        if seconds < 0:
            seconds = 0

        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
