# coding=utf-8
from components import Component
import cv2
import logging
import sys
import time


class Camera(Component):
    """
    IMX219 CSI Camera and USB camera.
    """

    def __init__(self,
                 device='/dev/video0',
                 width=1280,
                 height=720,
                 frame_rate=21,
                 flip_mode=0,
                 capture_width=3280,
                 capture_height=2464):
        """
        flip_mode = 0 - no flip
        flip_mode = 1 - rotate CCW 90
        flip_mode = 2 - flip vertically
        flip_mode = 3 - rotate CW 90
        """
        super(Camera, self).__init__()
        self.device = device
        self.width = width
        self.height = height
        self.frame_rate = frame_rate
        self.flip_mode = flip_mode
        self.capture_width = capture_width
        self.capture_height = capture_height

        self.camera = None

    def start(self) -> bool:
        if 'darwin' in sys.platform.lower() or 'windows' in sys.platform.lower():
            self.camera = cv2.VideoCapture(self.device)
        else:
            self.camera = cv2.VideoCapture(
                self._gstreamer_pipeline(
                    self.device,
                    capture_width=self.capture_width,
                    capture_height=self.capture_height,
                    output_width=self.width,
                    output_height=self.height,
                    framerate=self.frame_rate,
                    flip_method=self.flip_mode
                ),
                cv2.CAP_GSTREAMER
            )

        self.camera.read()
        time.sleep(2)  # warm up
        logging.info('Camera started.')
        return True

    def _gstreamer_pipeline(self, device, capture_width=3280, capture_height=2464,
                            output_width=224,
                            output_height=224,
                            framerate=21,
                            flip_method=0):
        if self.device == '/dev/video0':
            return 'nvarguscamerasrc sensor-id=0 ! video/x-raw(memory:NVMM), width=%d, height=%d, format=(string)NV12, framerate=(fraction)%d/1 ! nvvidconv flip-method=%d ! nvvidconv ! video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! videoconvert ! appsink' % (
                capture_width, capture_height, framerate, flip_method, output_width, output_height)
        else:
            return 'v4l2src device=%s ! videoconvert ! videoscale ! video/x-raw,width=%d,height=%d ! appsink' % (
                device, output_width, output_height)

    def run(self):
        while True:
            _, frame = self.camera.read()
            self.publish_message(frame)

    def shutdown(self):
        logging.info('Camera shutdown.')
