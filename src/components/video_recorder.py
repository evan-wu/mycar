# coding=utf-8
from components import Component
import cv2
import logging


class VideoRecorder(Component):
    """
    A simple video recorder.

    subscriptions: camera input, record switch
    """

    def __init__(self, width: int = 1280, height: int = 720, frame_rate: int = 7, path: str = None, name: str = None,
                 auto_start: bool = False):
        super(VideoRecorder, self).__init__()
        self.width = width
        self.height = height
        self.writer = cv2.VideoWriter((path or '.') + '/' + (name or 'capture.avi'),
                                      cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                      frame_rate,
                                      (width, height))
        logging.info('VideoRecorder saving video to {}/{}'.format(path or '.', name or 'capture.avi'))
        self.capture = None
        self.record = auto_start

    def start(self) -> bool:
        return True

    def run(self, stop_event):
        while stop_event.is_set():
            if self.capture is not None and self.record:
                self.writer.write(self.capture)

    def on_message(self, channel, content):
        if channel == self.subscription[0]:
            self.capture = content
        elif channel == self.subscription[1]:
            self.record = content

    def shutdown(self):
        logging.info('Stopping VideoRecorder')
        self.writer.release()
        del self.writer
