# coding=utf-8
from adafruit_servokit import ServoKit


class PCA9685:
    """
    PWM Controller using PCA9685 boards.
    """
    ANGLE_RANGE = (0, 180)
    THROTTLE_RANGE = (-1, 1)

    def __init__(self,
                 channels: int = 16,
                 address: int = 0x40,
                 frequency: int = 50,
                 busnum: int = None,
                 init_delay=0.1):
        servokit = ServoKit(channels=channels, address=address)
        self._servo = servokit

        esckit = ServoKit(channels=channels, address=address)
        self._esc = esckit

    def set_angle(self, channel: int, angle: int):
        """
        set angle 0 - 180
        """
        self._servo.servo[channel].angle = angle

    def set_throttle(self, channel: int, throttle: float):
        """
        set throttle -1 - 1
        """
        self._esc.continuous_servo[channel].throttle = throttle
