# coding=utf-8


def map_range(x, X_min, X_max, Y_min, Y_max):
    """
    Linear mapping between two ranges of values
    """
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range / Y_range

    y = Y_min + (x-X_min) / XY_ratio

    return y