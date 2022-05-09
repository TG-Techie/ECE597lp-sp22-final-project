from __future__ import annotations

try:  # adding types can make the code more readable, but circuitpython doesn't support it
    from typing import *
except ImportError:
    pass


class OpenCloseDetector:
    def __init__(
        self,
        *,
        drift_thres: float,
        door_close_thresh: float,
        door_open_thresh: float,
        debug_output: bool = True,
    ) -> None:
        """
        :param drift_thres: radians, the minumum angle a new sample has to be to be considered valid
        :param door_close_thresh: radians, the angle the door has to pass to be considered closed
        :param door_open_thresh: radians, the angle the door has to pass to be considered open
        """

        # input
        self.drift_thres = drift_thres
        self.door_close_thresh = door_close_thresh
        self.door_open_thresh = door_open_thresh
        self.debug_output = debug_output

        # internal state
        self.angle: float = 0
        self.door_is_open: bool = False

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
        if self.debug_output:
            print(f"({self.angle}, {sample}, 3.141592653589, -1)")
            print("")

    def get_event(self) -> None | bool:
        """
        Call to see if the status of the door has changed.
        :return: True if the door just opened, False if it just closed, None if it hasn't changed
        """

        if self.door_is_open and self.angle < self.door_close_thresh:
            self.door_is_open = False
            return False
        elif not self.door_is_open and self.angle > self.door_open_thresh:
            self.door_is_open = True
            return True
        else:
            return None
