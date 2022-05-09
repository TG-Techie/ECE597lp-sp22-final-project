import time


class DoorTimeTracker:
    def __init__(self):
        self.last_time_door_open = -1
        self.is_open_too_long = False

        self.door_open = False
        self.open_count = 0
        self.open_too_long_count = 0

    def calibrate(self):
        self.last_time_door_open = -1
        self.door_open = False

    def door_opened(self):
        self.last_time_door_open = time.monotonic()
        self.door_open = True
        self.open_count += 1
        print("[[door opened]]")
        time.sleep(0.25)

    def door_closed(self):
        self.door_open = False
        print("[[door closed]]")
        time.sleep(0.25)

    def open_too_long(self, now: float | None = None) -> bool:
        now = now or time.monotonic()  # if no now provided, use the current time

        ret = bool(self.door_open and now - self.last_time_door_open > 10)
        if ret and not self.is_open_too_long:
            self.open_too_long_count += 1
            print("[[door open too long]]")
            time.sleep(0.25)
        self.is_open_too_long = ret
        return ret
