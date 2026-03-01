"""
人脸检测模块
"""

import cv2
import numpy as np
import os
import sys
import platform
from pathlib import Path


def _get_video_capture_backend():
    """根据操作系统获取合适的 VideoCapture 后端

    Returns:
        int: OpenCV VideoCapture 后端标识
    """
    system = platform.system()

    if system == "Windows":
        # Windows: 使用 DirectShow 后端
        return cv2.CAP_DSHOW
    elif system == "Darwin":
        # macOS: 使用默认后端 (AVFoundation)
        return cv2.CAP_ANY
    elif system == "Linux":
        # Linux: 使用 V4L2 后端
        return cv2.CAP_V4L2
    else:
        # 默认使用系统原生后端
        return cv2.CAP_ANY


class FaceDetector:
    """人脸检测器"""

    def __init__(self):
        self.face_cascade = None
        self._load_cascade()

    def _get_cascade_path(self):
        """获取Haar Cascade模型文件路径"""
        # 方法1: 从项目resources目录加载
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cascade_path = os.path.join(base_dir, 'resources', 'haarcascade_frontalface_default.xml')
        if os.path.exists(cascade_path):
            return cascade_path

        # 方法2: 从PyInstaller打包的临时目录加载
        if hasattr(sys, '_MEIPASS'):
            cascade_path = os.path.join(sys._MEIPASS, 'resources', 'haarcascade_frontalface_default.xml')
            if os.path.exists(cascade_path):
                return cascade_path

        # 方法3: 从OpenCV数据目录加载
        opencv_cascade = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        if os.path.exists(opencv_cascade):
            return opencv_cascade

        return None

    def _load_cascade(self):
        """加载Haar Cascade分类器"""
        cascade_path = self._get_cascade_path()

        if cascade_path and os.path.exists(cascade_path):
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if not self.face_cascade.empty():
                return

        raise RuntimeError("无法加载人脸检测模型")

    def detect_faces(self, frame):
        """
        检测画面中的人脸

        Args:
            frame: OpenCV读取的帧（BGR格式）

        Returns:
            faces: 检测到的人脸列表 [(x, y, w, h), ...]
        """
        if self.face_cascade is None:
            return []

        # 转换为灰度图
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # 直方图均衡化，提高检测效果
        gray = cv2.equalizeHist(gray)

        # 检测人脸
        # scaleFactor: 每次缩放比例
        # minNeighbors: 检测区域相邻矩形的数量，越高越严格
        # minSize: 最小检测尺寸
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        return faces.tolist() if len(faces) > 0 else []

    def is_face_detected(self, frame):
        """
        判断是否检测到人脸

        Args:
            frame: OpenCV读取的帧

        Returns:
            bool: 是否检测到人脸
        """
        faces = self.detect_faces(frame)
        return len(faces) > 0


class Camera:
    """摄像头管理"""

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_opened = False

    def open(self):
        """打开摄像头"""
        # 根据操作系统选择合适的后端
        backend = _get_video_capture_backend()
        self.cap = cv2.VideoCapture(self.camera_index, backend)

        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {self.camera_index}")

        # 设置分辨率（降低分辨率提高性能）
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.is_opened = True
        return True

    def read(self):
        """
        读取下一帧

        Returns:
            ret: 是否成功读取
            frame: 图像帧
        """
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        """释放摄像头"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_opened = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
