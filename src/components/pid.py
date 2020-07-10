# coding=utf-8
from components import Component
import cv2
import logging
import pickle
import time
from applications.cv_utils import undistort_and_tansform
from applications.line_detection import detect_line_and_polyfit
import os

logger = logging.getLogger("PIDLineFollower")


class PIDLineFollower(Component):
    """
    Line follower using PID algorithm.

    subscriptions: camera image, start/stop signal, throttle increase/decrease signal
    publications: steering, throttle, image with control signal
    """
    def __init__(self,
                 calibration_result: str = './config/calibration_result.pkl',
                 roi: tuple = ((0, 0), (1280, 720)),
                 camera_offset: int = 0,
                 white_threshold=80,
                 steer_interval=0.02,
                 train_mode=False,
                 pid_params_file='./config/pid_coefficients.pkl',
                 line_detect_window_height=50,
                 line_detect_window_width=120
                 ):
        """
        Args:
            roi: region of image to find line, specify the top left and bottom right position.
            calibration_result: calibration result pickle file.
            camera_offset: camera offset regarding to the image horizontal center, can be negative(on the left)
            white_threshold: pixels smaller than this value will be marked as the black line.
            steer_interval: the interval between each steering control
            train_mode: whether training the PID params.
            pid_params_file: where to save(under train mode) or load the PID params.
            line_detect_window_height: line detection slide window height.
            line_detect_window_width: line detection slide window width.
        """
        super(PIDLineFollower, self).__init__()
        with open(calibration_result, 'br') as f:
            self.c_mtx, self.c_dist, self.c_corners, self.c_img_size = pickle.load(f)
        self.roi = roi
        self.camera_offset = camera_offset
        self.white_threshold = white_threshold
        self.steer_interval = steer_interval
        self.train_mode = train_mode
        self.pid_params_file = pid_params_file
        self.line_detect_window_height = line_detect_window_height
        self.line_detect_window_width = line_detect_window_width

        # internal state
        self.image = None
        self.moving = False
        self.last_not_found = 0

        # cross track error
        self.int_cte = 0  # integral cross track error
        self.prev_cte = 0  # previous cross track error

        if os.path.exists(pid_params_file):
            with open(pid_params_file, 'br') as f:
                self.pid_coeffs = pickle.load(f)
        else:
            # some default params
            self.pid_coeffs = [0.0361935681, 0.03901406179, 0.0003143881]

        if train_mode:
            self.d_coeffs = self.pid_coeffs / 10.0
            self.train_sum_error = 0.0
            self.train_best_error = 0.0
            self.training_step = 0
            self.training_epoch = 0
            self.tuning_coeff = 0  # start at tuning the first coefficient
            self.forward_tune = True

        # output control
        self.steering = 0.0
        self.throttle = 1

    def _preprocess_image(self, img):
        undist = undistort_and_tansform(img, self.c_mtx, self.c_dist, self.c_corners, self.c_img_size)

        roi_top_left, roi_bottom_right = self.roi[0], self.roi[1]
        roi = undist[roi_top_left[1]:roi_bottom_right[1], roi_top_left[0]:roi_bottom_right[0]]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        _, binary = cv2.threshold(gray, self.white_threshold, 255, cv2.THRESH_BINARY_INV)
        return binary

    def _find_and_fit_line(self, img) -> tuple:
        """
        Use pixel histogram to find line, fit a polynomial to calculate line position.

        Returns:
            line_position, car_position
        """
        binary = self._preprocess_image(img)
        # car at the middle
        car_position = binary.shape[1] // 2 - self.camera_offset

        polyfit, image_out = detect_line_and_polyfit(binary,
                                                     slide_window_height=self.line_detect_window_height,
                                                     slide_window_width=self.line_detect_window_width,
                                                     debug=len(self.publication) == 3)
        y = binary.shape[0] - 1
        x = polyfit[0] * y**2 + polyfit[1] * y + polyfit[2]

        if x <= 0:
            # line not found, stop the car
            now = time.time()
            if now - self.last_not_found > 5:
                logger.warning('Line is not found, check saved line_not_found_*.png image.')
                cv2.imwrite('./line_not_found_{}.png'.format(now), img)
                self.last_not_found = now
            return -1, car_position, image_out

        return x, car_position, image_out

    @staticmethod
    def _cte(line_center, car_position):
        """
        cross track error
        """
        return car_position - line_center

    def _twiddle_pid_params(self):
        logger.info('Saving PID coefficients at iteration {}, coefficients {}, delta {}'
                     .format(self.training_epoch, self.pid_coeffs, self.d_coeffs))
        with open(self.pid_params_file + str(self.training_epoch), 'bw') as f:
            pickle.dump(self.pid_coeffs, f)

        if self.training_epoch == 0:  # first run
            self.train_best_error = self.train_sum_error / self.training_step
            logger.info('Iteration {}, steps {}, PID coefficients {}, delta {}, best error {}'
                         .format(self.training_epoch,
                                 self.training_step,
                                 self.pid_coeffs,
                                 self.d_coeffs,
                                 self.train_best_error))
            self.pid_coeffs[self.tuning_coeff] += self.d_coeffs[self.tuning_coeff]
        else:
            logger.info('Iteration {}, steps {}, PID coefficients {}, delta {}, current error {}, best error {}'
                         .format(self.training_epoch,
                                 self.training_step,
                                 self.pid_coeffs,
                                 self.d_coeffs,
                                 self.train_sum_error / self.training_step,
                                 self.train_best_error))

            current_error = self.train_sum_error / self.training_step
            if self.forward_tune:
                if current_error < self.train_best_error:
                    self.train_best_error = current_error
                    self.d_coeffs[self.tuning_coeff] *= 1.1

                    # next param
                    self.tuning_coeff = (self.tuning_coeff + 1) % 3
                else:
                    self.pid_coeffs[self.tuning_coeff] -= 2 * self.d_coeffs[self.tuning_coeff]  # revert
                    self.forward_tune = False
            else:  # prev param
                if current_error < self.train_best_error:
                    self.train_best_error = current_error
                    self.d_coeffs[self.tuning_coeff] *= 1.1
                else:
                    self.pid_coeffs[self.tuning_coeff] += self.d_coeffs[self.tuning_coeff]
                    self.d_coeffs[self.tuning_coeff] *= .9

                self.forward_tune = True

                # next param
                self.tuning_coeff = (self.tuning_coeff + 1) % 3

            # next iteration
            self.pid_coeffs[self.tuning_coeff] += self.d_coeffs[self.tuning_coeff]

        # reset
        self.training_step = 0
        self.train_sum_error = 0
        self.training_epoch += 1

    def _pid_steering(self, cte):
        """
        Use the equation: new_steering = c0 * cte + c1 * cte_integrational + c2 * cte_differential
        to calculate the new steering.
        """
        diff_cte = cte - self.prev_cte
        self.prev_cte = cte
        self.int_cte += cte

        # proportional
        pid_p = self.pid_coeffs[0] * cte

        # differential
        pid_d = self.pid_coeffs[1] * diff_cte

        # integrational
        if abs(cte) <= 10:  # anti integerator windup (over shooting)
            self.int_cte = 0

        pid_i = self.pid_coeffs[2] * self.int_cte

        # anti windup via dynamic integrator clamping
        int_limit_max = 0.0
        int_limit_min = 0.0
        if pid_p < 1:
            int_limit_max = 1 - pid_p
        if pid_p > -1:
            int_limit_min = -1 - pid_p

        if pid_i > int_limit_max:
            pid_i = int_limit_max
        elif pid_i < int_limit_min:
            pid_i = int_limit_min

        # sum up
        steer = -(pid_p + pid_d + pid_i)

        # apply limits
        if steer < -1:
            return -1
        elif steer > 1:
            return 1
        else:
            return steer

    def start(self) -> bool:
        # check subscription
        if len(self.subscription) < 2:
            raise ValueError('Subscriptions to the camera image and start/stop signal as input are required!')

        return True

    def shutdown(self):
        pass

    def run(self, stop_event):
        while not stop_event.is_set():
            if self.image is not None and self.moving:
                line, car, image_out = self._find_and_fit_line(self.image)
                self.image = None
                if line > 0:
                    cte = PIDLineFollower._cte(line, car)
                    steering = self._pid_steering(cte)

                    if self.train_mode:
                        self.training_step += 1
                        self.train_sum_error += self.prev_cte ** 2

                    # output some info on the output image
                    cv2.line(image_out, (car, 0), (car, image_out.shape[0] - 1), (0, 0, 255), thickness=1)
                    cv2.putText(image_out, 'cte: {:.2f}'.format(cte), (30, 400), cv2.FONT_HERSHEY_SIMPLEX,
                                1, (0, 255, 0), thickness=1)
                    cv2.putText(image_out, 'steer: {:.2f}'.format(steering), (30, 435),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), thickness=1)

                    self.publish_message(steering, self.throttle, image_out)
                else:
                    self.publish_message(0, 0, None)
            else:
                self.publish_message(0, 0, None)

            time.sleep(self.steer_interval)  # TODO needed?

    def on_message(self, channel, content):
        if channel == self.subscription[0]:  # camera image
            self.image = content
        elif channel == self.subscription[1]:  # start/stop
            move = bool(content)
            if self.train_mode:
                if self.moving:
                    if not move:  # finish one training iteration
                        self._twiddle_pid_params()
            self.moving = move
        elif channel == self.subscription[2]:  # throttle scale
            self.throttle = content
