# coding=utf-8
from components import Component
from fcntl import ioctl
import logging
import os
import array
import struct

logger = logging.getLogger("JoystickController")


# Credits: Joystick refers to https://github.com/autorope/donkeycar/blob/dev/donkeycar/parts/controller.py
class JoystickController(Component):
    """
    Joystick Controller.

    publications: steering, throttle, autonomous, record, throttle scale
    """

    STEERING_AXIS = 'left_stick_horz'
    THROTTLE_AXIS = 'right_stick_vert'
    AUTONOMOUS_BUTTON = 'Y'
    RECORD_BUTTON = 'B'

    def __init__(self, axis_keys: dict, output_interval=0.02, button_keys: dict = {}, device='/dev/input/js0'):
        """
        Args:
            axis_keys: (dict): joystick axis key mapping.
            button_keys: (dict): joystick button key mapping.
            device: (str): the joystick input device.
        """
        super(JoystickController, self).__init__()
        self.device = device
        self.output_interval = output_interval

        self.throttle_scale = 1.0
        self.poll_delay = 0.1
        self.js = None
        self.js_name = None
        self.num_axes = 0
        self.num_buttons = 0

        # test required keys
        if JoystickController.STEERING_AXIS not in axis_keys:
            raise ValueError("steering axis '{}' not defined in 'axis_keys' in config file."
                             .format(JoystickController.STEERING_AXIS))

        if JoystickController.THROTTLE_AXIS not in axis_keys:
            raise ValueError("throttle axis '{}' not defined in 'axis_keys' in config file."
                             .format(JoystickController.THROTTLE_AXIS))

        # axes
        self.axis_names = {axis_keys[k]: k for k in axis_keys}  # key mapping to readable name
        self.axis_map = []
        self.axis_states = {}
        self.axis_trigger_map = {}

        # buttons
        self.button_names = {button_keys[k]: k for k in button_keys}  # key mapping to readable name
        self.button_map = []
        self.button_states = {}
        self.button_down_trigger_map = {}
        self.button_up_trigger_map = {}

        # output values
        self.steering, self.throttle, self.autonomous, self.record = 0.0, 0.0, False, False
        self.last_output = 0
        if not os.path.exists(self.device):
            raise ValueError('Joystick device: {} is not found.'.format(self.device))

    def _init_joystick(self):
        self.js = open(self.device, 'rb')
        # Get the device name
        buf = array.array('B', [0] * 64)
        ioctl(self.js, 0x80006a13 + (0x10000 * len(buf)), buf)  # JSIOCGNAME(len)
        self.js_name = buf.tobytes().decode('utf-8')
        logger.info('Device name: {}'.format(self.js_name))

        # Get number of axes and buttons.
        buf = array.array('B', [0])
        ioctl(self.js, 0x80016a11, buf)  # JSIOCGAXES
        self.num_axes = buf[0]

        buf = array.array('B', [0])
        ioctl(self.js, 0x80016a12, buf)  # JSIOCGBUTTONS
        self.num_buttons = buf[0]

        # Get the axis map.
        buf = array.array('B', [0] * 0x40)
        ioctl(self.js, 0x80406a32, buf)  # JSIOCGAXMAP

        for axis in buf[:self.num_axes]:
            axis_name = self.axis_names.get(axis, 'unknown(0x%02x)' % axis)
            self.axis_map.append(axis_name)
            self.axis_states[axis_name] = 0.0

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(self.js, 0x80406a34, buf)  # JSIOCGBTNMAP

        for btn in buf[:self.num_buttons]:
            btn_name = self.button_names.get(btn, 'unknown(0x%03x)' % btn)
            self.button_map.append(btn_name)
            self.button_states[btn_name] = 0

        logger.info('%d axes found: %s' % (self.num_axes, ', '.join(self.axis_map)))
        logger.info('%d buttons found: %s' % (self.num_buttons, ', '.join(self.button_map)))

    def start(self) -> bool:
        self._init_joystick()
        # init trigger map
        self._init_trigger_maps()
        return True

    def _init_trigger_maps(self):
        """
        init set of mapping from buttons to function calls
        """
        self.button_down_trigger_map = {
            'select': None,
            'start': None,

            'B': self._toggle_record,
            'Y': self._toggle_autonomous,
            'A': None,
            'X': None,

            'R1': self._increase_max_throttle,
            'L1': self._decrease_max_throttle,

            'R2': None,
            'L2': None,
        }

        self.button_up_trigger_map = {
            'R2': None,
            'L2': None,
        }

        self.axis_trigger_map = {
            'left_stick_horz': self._set_steering,
            'right_stick_vert': self._set_throttle,
            'dpad_leftright': None,
            'dpad_up_down': None,
        }

    def _set_steering(self, axis_val):
        self.steering = axis_val

    def _set_throttle(self, axis_val):
        # this value is often reversed, with positive value when pulling down
        self.throttle = (-1 * axis_val * self.throttle_scale)

    def _toggle_record(self):
        """
        toggle recording on/off
        """
        self.record = not self.record
        logger.info('recording: {}'.format(self.record))

    def _toggle_autonomous(self):
        """
        toggle autonomous on/off
        """
        self.autonomous = not self.autonomous
        logger.info('autonomous: {}'.format(self.autonomous))

    def _increase_max_throttle(self):
        """
        increase throttle scale setting
        """
        self.throttle_scale = round(min(1.0, self.throttle_scale + 0.01), 2)
        logger.info('throttle_scale: {}'.format(self.throttle_scale))

    def _decrease_max_throttle(self):
        """
        decrease throttle scale setting
        """
        self.throttle_scale = round(max(0.0, self.throttle_scale - 0.01), 2)
        logger.info('throttle_scale: {}'.format(self.throttle_scale))

    def run(self, stop_event):
        while not stop_event.is_set():
            # poll the joystick input
            button, button_state, axis, axis_val = self._poll_joystick()

            if axis is not None and axis in self.axis_trigger_map and self.axis_trigger_map[axis]:
                self.axis_trigger_map[axis](axis_val)

            if button and button_state >= 1 and button in self.button_down_trigger_map and self.button_down_trigger_map[button]:
                self.button_down_trigger_map[button]()

            if button and button_state == 0 and button in self.button_up_trigger_map and self.button_up_trigger_map[button]:
                self.button_up_trigger_map[button]()

            self.publish_message(self.steering, self.throttle, self.autonomous, self.record, self.throttle_scale)

    def _poll_joystick(self):
        """
        Query the state of the joystick, return button which was pressed,
        and axis which was moved, if any. button_state will be None, 1, or 0 if no changes,
        pressed, or released. axis_val will be a float from -1 to +1.
        Button and axis will be the string label determined by the axis map in init.
        """
        button = None
        button_state = None
        axis = None
        axis_val = None

        evbuf = self.js.read(8)

        if evbuf:
            tval, value, typev, number = struct.unpack('IhBB', evbuf)

            if typev & 0x80:
                # ignore initialization event
                return button, button_state, axis, axis_val

            if typev & 0x01:
                button = self.button_map[number]
                if button:
                    self.button_states[button] = value
                    button_state = value
                    logger.info('button: {} state: {}'.format(button, value))

            if typev & 0x02:
                axis = self.axis_map[number]
                if axis:
                    fvalue = value / 32767.0
                    self.axis_states[axis] = fvalue
                    axis_val = fvalue
                    logger.info('axis: {}, val: {}'.format(axis, fvalue))

        return button, button_state, axis, axis_val

    def shutdown(self):
        pass
