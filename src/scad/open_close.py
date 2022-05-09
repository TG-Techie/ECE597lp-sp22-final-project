from __future__ import annotations

try:  # adding types can make the code more readable, but circuitpython doesn't support it
    from typing import *
except ImportError:
    pass


class OpenCloseDetector:
    def __init__(self, *, drift_thres: float) -> None:

        self.angle: float = 0
        self.door_is_open: bool = False
        self.drift_thres = drift_thres

    def calibrate(self) -> None:
        self.angle = 0
        self.door_is_open = False
        print("calibrating!!")

    def new_sample(self, sample: float, dt: float) -> None:
        d_angle: float = sample * dt
        d_thresh = self.drift_thres * dt

        # skip this if the new sample is below the threshold
        if -d_thresh < d_angle < d_thresh:
            pass

        # continue the integration
        else:
            self.angle += d_angle

        # print("Gyro X:%.2f, Y: %.2f, Z: %.2f rads/s" % (gyro))
        print(f"({sample}, {self.angle}, 3.141592653589, -1)")
        print("")

    def check_door_event(self) -> None | bool:
        """
        Call to see if the status of the door has changed.
        :return: True if the door just opened, False if it just closed, None if it hasn't changed
        """

        if self.angle > self.threshold:
            pass

        raise NotImplementedError
