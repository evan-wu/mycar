# coding=utf-8
import cv2
import numpy as np
import pickle
import logging


def calibrate_camera(chessboard_input_images: list, chessboard_corners=(9, 6), debug=False):
    """
    Do camera calibration.
    """
    assert type(chessboard_input_images) is list, 'input should be a list of images'
    # Note the image origin is (0, 0), the bottom right corner is (8, 5)

    obj_points = []  # 3D points in real world space
    img_points = []  # 2D points in image plane

    # world points always on flat plane, like (0, 0, 0), (1, 0, 0), (2, 0, 0) ..., (8, 5, 0), according to image space
    obj_points_for_one_image = np.zeros((chessboard_corners[0] * chessboard_corners[1], 3), np.float32)
    obj_points_for_one_image[:, :2] = np.mgrid[0:chessboard_corners[0], 0:chessboard_corners[1]].T.reshape(-1, 2)  # x, y coordinates

    for chessboard_image in chessboard_input_images:
        gray = cv2.cvtColor(chessboard_image, cv2.COLOR_BGR2GRAY)
        # find chessboard corners
        ret, corners = cv2.findChessboardCorners(gray, chessboard_corners, None)  # corners in image space
        if debug:
            img = cv2.drawChessboardCorners(chessboard_image, chessboard_corners, corners, ret)
            cv2.imshow('Corners', img)
            cv2.waitKey()

        if ret is True:
            img_points.append(corners)
            obj_points.append(obj_points_for_one_image)

    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, gray.shape[::-1], None, None)
    return mtx, dist, corners, gray.shape[::-1]


def calibrate_and_save(input, output):
    """
    Helper method to do camera calibration and save the result using pickle.
    """
    if type(input) is str:
        img = cv2.imread(input)
        cv2.imshow('img', img)
        cv2.waitKey()

        mtx, dist, corners, img_size = calibrate_camera([img], debug=True)
        undistorted = undistort(img, mtx, dist)
        cv2.imshow('undistorted', undistorted)
        cv2.waitKey()

        ret = undistort_and_tansform(img, mtx, dist, corners, img_size)
        cv2.imshow('ret', ret)
        cv2.waitKey()
    else:
        imgs = []
        for i in input:
            imgs.append(cv2.imread(i))
        mtx, dist, corners, img_size = calibrate_camera(imgs)

    with open(output, 'bw') as f:
        pickle.dump((mtx, dist, corners, img_size), f)
    logging.info('done!')


def undistort(image, mtx, dist, calibrate_image_size: tuple = None):
    if calibrate_image_size is not None:
        h, w = image.shape[:2]
        new_camera_mtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, calibrate_image_size, 1, (w, h))
        return cv2.undistort(image, mtx, dist, None, new_camera_mtx)
    else:
        return cv2.undistort(image, mtx, dist, None, mtx)


def perspective_transform(image, src_points, dest_points, dst_size=None):
    M = cv2.getPerspectiveTransform(src_points, dest_points)
    # Warp the image using OpenCV warpPerspective()
    if dst_size is None:
        dst_size = (image.shape[1], image.shape[0])
    return cv2.warpPerspective(image, M, dst_size)


def undistort_and_tansform(image, mtx, dist, calibrate_corners, calibrate_image_size, dst_size: tuple = None,
                           chessboard_corners=(9, 6)):
    """
    Do undistortion and then use the chessboard outer 4 corners to do perspective transform.
    """
    undistorted = undistort(image, mtx, dist)

    # For source points I'm grabbing the outer four detected corners
    nx, ny = chessboard_corners
    # top left, top right, bottom right, bottom left
    src = np.float32([calibrate_corners[0], calibrate_corners[nx - 1], calibrate_corners[-1], calibrate_corners[-nx]])
    src = cv2.undistortPoints(src, mtx, dist, P=mtx)

    # map the 4 points to a bird's view, bottom 2 points unchanged
    # src dimension is (4, 1, 2)
    x_span = src[2][0][0] - src[3][0][0]
    y_span = x_span / chessboard_corners[0] * chessboard_corners[1]
    # change the top 2 points to a plane position
    dst = np.float32([[src[3][0][0], src[3][0][1] - y_span], [src[2][0][0], src[2][0][1] - y_span],
                      src[2][0],
                      src[3][0]])
    if dst_size is not None:
        height_increment = dst_size[1] - calibrate_image_size[1]
        dst[:, 1] += height_increment  # move the dst points down to show more

    transformed = perspective_transform(undistorted, src, dst, dst_size)
    return transformed


def save_video_frame(file, save_prefix, wait_time=3000):
    """
    View and save video frame. Press 's' to save.
    """
    capture = cv2.VideoCapture(file)
    seq = 1
    save_seq = 1
    while capture.isOpened():
        ret, frame = capture.read()
        print('frame: {}'.format(seq))
        cv2.imshow('frames', frame)
        key = cv2.waitKey(wait_time) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite(save_prefix + '{}.png'.format(save_seq), frame)
            save_seq += 1
        seq += 1

    capture.release()
    cv2.destroyAllWindows()
