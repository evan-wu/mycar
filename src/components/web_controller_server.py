# coding=utf-8
"""
Web UI to control car movement and view camera stream.
"""
from flask import Flask, request, Response, render_template
import zmq
import logging
import sys
import pickle
import cv2
import time
from threading import Thread


logging.getLogger('werkzeug').setLevel(logging.ERROR)

control_channel = sys.argv[1]
camera_channel = sys.argv[2]
output_width = int(sys.argv[3])
output_height = int(sys.argv[4])
frame_rate = int(sys.argv[5])

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # no cache

# the live image
captured = None
last_captured = 0


def on_camera_image(message):
    global last_captured
    if time.time() - last_captured < 1.0 / frame_rate:
        return

    frame = pickle.loads(message)
    frame = cv2.resize(frame, (480, 270))
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 20]
    _, buffer = cv2.imencode('.jpg', frame, encode_param)
    global captured
    captured = buffer.tostring()
    last_captured = time.time()


# zmq CAN
context = zmq.Context.instance()
sub = context.socket(zmq.SUB)
sub.connect("tcp://localhost:6000")
sub.subscribe(camera_channel)

push = context.socket(zmq.PUSH)
push.connect("tcp://localhost:6001")


# zmq camera image listener
def listener():
    while True:
        try:
            events = sub.poll(timeout=0.005)
            for i in range(events):
                multipart = sub.recv_multipart()
                on_camera_image(multipart[1])
        except Exception as e:
            print(str(e))


listener_thread = Thread(target=listener)
listener_thread.daemon = True
listener_thread.start()


def gen_frames():
    global captured
    while True:
        # get the camera frame
        if captured is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + captured + b'\r\n')  # concat frame one by one and show result


@app.route('/control')
def send_control():
    global push
    push.send_multipart(['web_control'.encode(), pickle.dumps(request.args)])
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
