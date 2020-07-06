# coding=utf-8
import numpy as np
import cv2


def base_hist(img, bottom_half=True):
    # Grab only the bottom half of the image
    # Lane lines are likely to be mostly vertical nearest to the car
    if bottom_half:
        to_check = img[img.shape[0]//2:, :]
    else:
        to_check = img
    # Sum across image pixels vertically - make sure to set an `axis`
    # i.e. the highest areas of vertical lines should be larger values
    histogram = np.sum(to_check, axis=0)
    return histogram


def slide_window_find(binary, window_height=50, window_width=120, recenter_pixels=30, debug_output=False):
    """
    Args:
        window_height: Choose the height of sliding windows.
        window_width: Set the width of the windows.
        recenter_pixels: Set minimum number of pixels found to recenter window.
        debug_output: If output an image containing the windows.
    """
    out_img = None
    if debug_output:
        # Create an output image to draw on and visualize the result
        out_img = np.dstack((binary, binary, binary))

    histogram = base_hist(binary)
    line_base = np.argmax(histogram)

    # sliding window
    # number of windows
    nwindows = np.int(binary.shape[0] // window_height)
    # Identify the x and y positions of all nonzero (i.e. activated) pixels in the image
    nonzero = binary.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])

    # Current positions to be updated later for each window in nwindows
    line_current = line_base
    # Create empty lists to receive line pixel indices
    line_inds = []

    # Step through the windows one by one
    for window in range(nwindows):
        # Identify window boundaries in x and y
        win_y_low = binary.shape[0] - (window + 1) * window_height
        win_y_high = binary.shape[0] - window * window_height
        win_x_low = line_current - window_width//2
        win_x_high = line_current + window_width//2

        if debug_output:
            # Draw the window on the visualization image
            cv2.rectangle(out_img, (win_x_low, win_y_low), (win_x_high, win_y_high), (0, 255, 0), 1)

        # Identify the nonzero pixels in x and y within the window
        good_inds = (
                (nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                (nonzerox >= win_x_low) & (nonzerox < win_x_high)
        ).nonzero()
        good_inds = good_inds[0]
        line_inds.append(good_inds)

        # If found > pixels, recenter next window on their mean position
        if len(good_inds) > recenter_pixels:
            line_current = np.int(np.mean(nonzerox[good_inds]))

    # Concatenate the arrays of indices (previously was a list of lists of pixels)
    line_inds = np.concatenate(line_inds)

    linex = nonzerox[line_inds]
    liney = nonzeroy[line_inds]
    return linex, liney, out_img


def detect_line_and_polyfit(binary, slide_window_height=50, slide_window_width=120, recenter_pixels=30, order=2, debug=False):
    assert binary.ndim == 2, 'input image should be binary, 1 channel'
    # Find line pixels first
    linex, liney, out_img = slide_window_find(binary,
                                              window_height=slide_window_height,
                                              window_width=slide_window_width,
                                              recenter_pixels=recenter_pixels,
                                              debug_output=debug)
    # Fit a second order polynomial
    if linex is not None and len(linex) > 0:
        fit = np.polyfit(liney, linex, order)
        if debug:
            # Generate x and y values for plotting
            ploty = np.linspace(0, binary.shape[0] - 1, binary.shape[0])
            if order == 2:
                fitx = fit[0] * ploty ** 2 + fit[1] * ploty + fit[2]
            elif order == 1:
                fitx = fit[0] * ploty + fit[1]
            elif order == 3:
                fitx = fit[0] * ploty ** 3 + fit[1] * ploty ** 2 + fit[2] * ploty + fit[3]
            else:
                raise Exception('order in [1,2,3] is supported')
            pts = np.array([[fitx[i], ploty[i]] for i in range(len(ploty))], np.int32)
            pts = np.reshape(pts, (-1, 1, 2))
            cv2.polylines(out_img, [pts], isClosed=False, color=(0, 255, 0), thickness=2)
    else:
        fit = [0, 0, 0]
    return fit, out_img
