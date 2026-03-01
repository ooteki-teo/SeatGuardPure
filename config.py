"""
配置管理模块
"""

import json
import os
from pathlib import Path


class Config:
    """应用程序配置"""

    # 默认配置
    DEFAULT_CONFIG = {
        # 提醒时长/已坐时间（分钟）
        'reminder_duration': 40,
        # 休息时间/宽限期（秒）
        'grace_period': 120,
    }

    # 配置保存路径
    CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.seat_guard_config.json')

    def __init__(self):
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
        # 确保配置有效（清理旧配置）
        if 'reminder_duration' not in self.config:
            self.config['reminder_duration'] = 40
        if 'grace_period' not in self.config:
            self.config['grace_period'] = 120
        self.save()

    def reset_to_default(self):
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()

    def load(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
        except Exception:
            pass  # 使用默认配置

    def save(self):
        """保存配置到文件"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    @property
    def reminder_duration(self):
        """已坐时间（分钟）"""
        return int(self.config.get('reminder_duration', 40))

    @reminder_duration.setter
    def reminder_duration(self, value):
        self.config['reminder_duration'] = int(value)
        self.save()

    @property
    def grace_period(self):
        """休息时间/宽限期（秒）"""
        return int(self.config.get('grace_period', 120))

    @grace_period.setter
    def grace_period(self, value):
        self.config['grace_period'] = value
        self.save()
