from __future__ import annotations

import time
import board
import digitalio
import keypad
import pwmio

WARN_AFTER_OPEN = 1 / 3  # minutes
SAMPLE_INDEX = 0  # x on the sparkfun icm-20648 board
LOOP_SLEEP_TIME = 0.01  # seconds
USE_BLUETOOTH = True
DRIFT_THRESH = 0.1
PRINT_USART_EVERY = 4  # seconds

DOOR_CLOSED_THRESH = 0.3  # radians
DOOR_OPENED_THRESH = 0.35  # radians


# constatnts
DOOR_OPENED = True
DOOR_CLOSED = False
NO_EVENT = None

# pretend import typing
try:
    from typing import *
except:
    pass

# ble imports
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# perispheral imports
from adafruit_icm20x import ICM20948

# our imports
from scad.open_close import OpenCloseDetector
from scad.tracker import DoorTimeTracker

# --- init BLE and prepare the adverisement type for later ---
ble = BLERadio()
ble.name = "Jay-dev"
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

if hasattr(board, "SWITCH"):
    print("using switch")
    switch = keypad.Keys([board.SWITCH], value_when_pressed=False, pull=True)
else:
    switch = None

if hasattr(board, "D10"):
    print("using alarm")
    # the alarm pin is attached to a peizo buzzer
    alarm = pwmio.PWMOut(
        getattr(board, "D10"),
        frequency=440,
        duty_cycle=1 << 14,
        variable_frequency=True,
    )
else:
    alarm = None

led = digitalio.DigitalInOut(getattr(board, "LED", getattr(board, "RED_LED", None)))
led.switch_to_output()

# from adafruit_ble import BLERadio
# from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
# from adafruit_ble.services.nordic import UARTService
# from adafruit_bluefruit_connect.packet import Packet
# from adafruit_bluefruit_connect.button_packet import ButtonPacket

# --- setup peripherals ---
i2c = board.I2C()
icm = ICM20948(i2c, address=0x69)

# --- processing ---
tracker = DoorTimeTracker()
detector = OpenCloseDetector(
    # future, link the tracker to the detector with the args below
    drift_thres=DRIFT_THRESH,
    door_close_thresh=DOOR_CLOSED_THRESH,
    door_open_thresh=DOOR_OPENED_THRESH,
    debug_output=False,
)


# --- misc functions ---
def process_sample(now: float, then: float):
    detector.new_sample(
        sample=icm.gyro[SAMPLE_INDEX],
        dt=now - then,
    )


def readline():
    if not USE_BLUETOOTH:
        return None
    else:
        uart.readline()


def calibrate():
    print("please close the door, the device will calibrate itself in 5 seconds...")
    for left in range(5, 1, -1):
        print(f"{left}...")
        time.sleep(1)
    else:
        detector.calibrate()
        tracker.calibrate()
        silence_the_alarm()


def check_for_button_press():
    if switch is None:
        return
    event = switch.events.get()
    if event is None:
        return
    elif event.released:
        print("button pressed, starting calibration...")
        calibrate()


def wait_for_connection(run_samples: bool = True):
    print("Waiting for connection...")
    ble.start_advertising(advertisement)
    last_print = time.monotonic()

    if not USE_BLUETOOTH:
        return

    last_loop = time.monotonic()
    while not ble.connected:
        now = time.monotonic()

        # refresh the angle measurment
        if run_samples:
            detector.new_sample(sample=icm.gyro[SAMPLE_INDEX], dt=now - last_loop)
            last_loop = now

        # print status every second
        if now - last_print > 1:
            print("connecting...", now)
            last_print = now

    else:
        # ble.stop_advertising()
        print("Connected!")


def sound_the_alarm():
    if alarm is not None and alarm.duty_cycle <= 0.1:
        alarm.duty_cycle = 1 << 14
    led.value = True


def silence_the_alarm():
    if alarm is not None:
        alarm.duty_cycle = 0
    led.value = False


_last_usart_print = time.monotonic()


def poll_usart_print(now: float | None = None):
    global _last_usart_print
    now = now or time.monotonic()

    if now - _last_usart_print > PRINT_USART_EVERY:
        _last_usart_print = now
        msg = (
            "{\n"
            + f"""
                "kind" : "status",
                "angle": {detector.angle},
                "time_monotonic": {time.monotonic()},
                "unattended_count": {tracker.open_too_long_count},
                "is_unattended": {tracker.is_open_too_long},
                "open_count": {tracker.open_count},
                "is_door_open": {str(tracker.door_open).lower()}\n"""
            + "}\n"
        ).replace("    ", " ")
        print(msg)
        if ble.connected:
            uart.write(msg)


globals = locals()


def eval_msg(msg: str, *, __globals: dict = globals):
    print("got msg:", repr(msg))
    try:

        ret = (
            "{\n"
            + f"""
                "kind" : "eval-okay",
                "msg" : {repr(str(msg))}
                "eval": {repr(str(eval((msg))))}\n"""
            + "}\n"
        )

    except Exception as e:
        print("error:", e)
        ret = (
            "{\n"
            + f"""
                    "kind" : "eval-error",
                    "msg" : {repr(str(msg))}
                    "error": {repr(str(e))}\n"""
            + "}\n"
        )

    print("sending:", str(ret))
    if ble.connected:
        uart.write(ret + "\n")


# --- buisness logic ---
def main():
    print("starting advertising...")
    wait_for_connection(run_samples=False)
    calibrate()

    while True:
        main_loop()


last_time = time.monotonic()


def main_loop():
    global last_time
    now = time.monotonic()

    check_for_button_press()

    if not ble.connected and USE_BLUETOOTH:
        print("disconnected")
        wait_for_connection()  # no timeout
        print(f"door used X times, left open Y times")
    # read from the UART and dispatch to the appropriate handler (if any)

    s = uart.readline()
    if s:
        print("got:", s)
        eval_msg(s)

    poll_usart_print(now)

    process_sample(then=last_time, now=now)
    event = detector.get_event()

    # then an door is open
    if event is True:
        tracker.door_opened()
    # check if the door is open for too long
    elif event is False:
        silence_the_alarm()
        tracker.door_closed()
    elif tracker.door_open and tracker.open_too_long(now):
        sound_the_alarm()
    else:
        pass

    last_time = now
    time.sleep(LOOP_SLEEP_TIME)


if __name__ == "__main__":

    # while True:
    #     wait_for_connection(run_samples=False)
    #     print("Waiting to connect")
    #     while not ble.connected:
    #         pass
    #     print("Connected")
    #     while ble.connected:
    #         s = uart.readline()
    #         if s:
    #             try:
    #                 result = str(eval(s))
    #             except Exception as e:
    #                 result = repr(e)
    #             uart.write(result.encode("utf-8"))

    main()
    # while True:
    #     time.sleep(1)
    #     sound_the_alarm()
