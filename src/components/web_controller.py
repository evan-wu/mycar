# coding=utf-8
from components import Component
import os
import subprocess
import logging
from utils import map_range
import time


class WebController(Component):
    """
    Web UI to control the movement of the Car.
    """

    def __init__(self,
                 stream_width=480,
                 stream_height=270,
                 stream_frame_rate=10,
                 min_control_interval=0.02
                 ):
        super(WebController, self).__init__()
        self.stream_width = stream_width
        self.stream_height = stream_height
        self.stream_frame_rate = stream_frame_rate
        self.min_control_interval = min_control_interval

        self.image = None
        self.web_server = None

        # controls
        self.throttle = 0.0
        self.steering = 0.0
        self.record = False
        self.autonomous = False
        self.last_control_time = 0
        self.last_stream_time = 0

    def start(self):
        # start web server
        pwd = os.path.abspath('.')
        if pwd.endswith('src'):
            pwd = os.path.abspath('components')
        else:
            pwd = os.path.abspath('src/components')

        self.web_server = subprocess.Popen(
            ["python3", pwd + "/web_controller_server.py",
             self.subscription[0],  # web controls signal
             self.subscription[1],  # camera live stream
             str(self.stream_width),
             str(self.stream_height),
             str(self.stream_frame_rate)])

        logging.info('WebController started.')

    def on_message(self, channel, control_input):
        if channel == self.subscription[0]:  # the first is the web control signal channel
            if time.time() - self.last_control_time < self.min_control_interval:
                return None

            logging.info('control input: {}'.format(control_input))
            if 'steer' in control_input:
                steer = map_range(int(control_input['steer']), -100.0, 100.0, -1.0, 1.0)
                self.steering = steer
            if 'throttle' in control_input:
                throttle = map_range(int(control_input['throttle']), -170.0, 170.0, -1.0, 1.0)
                self.throttle = throttle
            if 'record' in control_input:
                self.record = str(control_input['record']) == 'true'
            if 'auto' in control_input:
                self.autonomous = str(control_input['auto']) == 'true'

            self.publish_message(self.steering, self.throttle, self.record, self.autonomous)
            self.last_control_time = time.time()

    def shutdown(self):
        self.web_server.kill()
        logging.info('WebController shutdown.')
