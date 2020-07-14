# coding=utf-8
from components import Component
import cv2
import logging
import time

logger = logging.getLogger("VideoRecorder")


class VideoRecorder(Component):
    """
    A simple video recorder.

    subscriptions: camera input, record switch
    """

    def __init__(self, path: str = None, name: str = None,
                 auto_start: bool = False):
        super(VideoRecorder, self).__init__()
        logger.info('VideoRecorder will save video to {}/{}'.format(path or '.', name or 'capture.avi'))
        self.path = path
        self.name = name
        self.capture = None
        self.record = auto_start

        self.start_time = 0
        self.fps = 0
        self.fps_set = False
        self.writer = None

    def on_message(self, channel, content):
        if channel == self.subscription[0] and content is not None:
            self.capture = content

            if self.start_time == 0:
                self.start_time = time.time()

            elapsed = (time.time() - self.start_time)
            if not self.fps_set and elapsed < 1.0:
                self.fps += 1
            elif not self.fps_set:
                self.fps = round((self.fps + 1.0) / elapsed, 2)
                logger.info('Got FPS: {}, width: {}, height: {}'.format(self.fps, self.capture.shape[1],
                                                                        self.capture.shape[0]))
                self.fps_set = True
                self.writer = cv2.VideoWriter((self.path or '.') + '/' + (self.name or 'capture.avi'),
                                              cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                              self.fps,
                                              (self.capture.shape[1], self.capture.shape[0]))
            elif self.record:
                self.writer.write(self.capture)

        elif channel == self.subscription[1]:
            self.record = content

    def shutdown(self):
        logger.info('Stopping VideoRecorder')
        if self.writer is not None:
            self.writer.release()
            del self.writer
