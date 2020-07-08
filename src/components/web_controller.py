# coding=utf-8
from components import Component
import logging
from utils import map_range
import time
from flask import Flask, request, Response, render_template
import cv2

logging.getLogger('werkzeug').setLevel(logging.ERROR)


class WebController(Component):
    """
    Web UI to control the movement of the Car.

    subscriptions: camera image
    publications: steering, throttle, record, autonomous
    """

    def __init__(self,
                 stream_width=480,
                 stream_height=270,
                 stream_frame_rate=20,
                 min_control_interval=0.02
                 ):
        super(WebController, self).__init__()
        self.stream_width = stream_width
        self.stream_height = stream_height
        self.stream_frame_rate = stream_frame_rate
        self.min_control_interval = min_control_interval

        self.image = None

        # controls
        self.throttle = 0.0
        self.steering = 0.0
        self.record = False
        self.autonomous = False
        self.last_stream_time = 0

    def start(self) -> bool:
        logging.info('WebController started.')
        return True

    def run(self, stop_event):
        app = Flask(__name__)
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # no cache

        def gen_frames():
            while True:
                # get the camera frame
                if self.image is not None and (time.time() - self.last_stream_time) > (1.0 / self.stream_frame_rate):
                    self.last_stream_time = time.time()

                    frame = cv2.resize(self.image, (480, 270))
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 20]
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    captured = buffer.tostring()

                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + captured + b'\r\n')  # concat frame one by one

        @app.route('/control')
        def send_control():
            control_input = request.args
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
            return ''

        @app.route('/video_feed')
        def video_feed():
            """Video streaming route. Put this in the src attribute of an img tag."""
            return Response(gen_frames(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')

        @app.route('/')
        def index():
            """Video streaming home page."""
            return render_template('index.html')

        app.run(host='0.0.0.0', port=8080)

    def on_message(self, channel, image):
        self.image = image

    def shutdown(self):
        logging.info('WebController shutdown.')
