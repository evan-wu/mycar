# coding=utf-8
from components import Component
from utils.pca9685 import PCA9685
from utils import map_range
import logging

pca9685 = PCA9685()


class PWMSteering(Component):
    """
    Send PWM to servo to control the turning of the Car.
    """
    MIN_STEERING = -1
    MAX_STEERING = 1

    def __init__(self,
                 channel: int,
                 straight_angle: int = 105,
                 full_right_angle: int = 50,
                 full_left_angle: int = 150):
        """
        defaults of a 90 degree servo.

        Args:
            channel: the output channel of the PCA9685 board.
            straight_angle: PWM angle to go straight.
            full_right_angle: PWM angle to turn full right.
            full_left_angle: PWM angle to turn full left.
        """
        super(PWMSteering, self).__init__()
        self.channel = channel
        self.full_right_angle = full_right_angle
        self.full_left_angle = full_left_angle
        self.straight_angle = straight_angle

        # init direction
        self.angle = straight_angle

    def start(self):
        logging.info('PWM Steering started.')

    def on_message(self, channel, angle):
        """
        Args:
            channel:
            angle: float: -1 to 1
        """
        if angle == 0:
            pca9685.set_angle(self.channel, self.straight_angle)
        elif angle is not None:  #
            pca9685.set_angle(self.channel,
                              int(map_range(angle, self.MIN_STEERING, self.MAX_STEERING, self.full_left_angle,
                                            self.full_right_angle)))

    def shutdown(self):
        logging.info('PWM Steering shutdown.')


class PWMThrottle(Component):
    """
    Send PWM to ESC to control the speed of the Car.
    """

    def __init__(self,
                 channel: int,
                 min_throttle: float = -1,
                 max_throttle: float = 1
                 ):
        super(PWMThrottle, self).__init__()
        self.channel = channel
        self.min_throttle = min_throttle
        self.max_throttle = max_throttle

        # init throttle
        self.throttle = 0

    def start(self):
        logging.info('PWM Throttle started.')

    def on_message(self, channel, throttle):
        if throttle == 0:
            pca9685.set_throttle(self.channel, 0)
        elif throttle is not None:
            pca9685.set_throttle(self.channel, map_range(throttle, -1, 1, self.min_throttle, self.max_throttle))

    def shutdown(self):
        logging.info('PWM Throttle shutdown.')
