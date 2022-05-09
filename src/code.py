import time
import board

SAMPLE_INDEX = 0  # x on the sparkfun icm-20648 board
LOOP_SLEEP_TIME = 0.01  # seconds
USE_BLUETOOTH = False
DRIFT_THRESH = 0.1

# ble imports
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# perispheral imports
from adafruit_icm20x import ICM20948

# our imports
from scad.open_close import OpenCloseDetector
from scad.tracker import DoorTracker

# --- init BLE and prepare the adverisement type for later ---
ble = BLERadio()
ble.name = "Jay-dev"
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

# from adafruit_ble import BLERadio
# from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
# from adafruit_ble.services.nordic import UARTService
# from adafruit_bluefruit_connect.packet import Packet
# from adafruit_bluefruit_connect.button_packet import ButtonPacket

# --- setup peripherals ---
i2c = board.I2C()
icm = ICM20948(i2c, address=0x69)

# --- processing ---
door = DoorTracker()

detector = OpenCloseDetector(
    # future, link the tracker to the detector with the args below
    drift_thres=DRIFT_THRESH,
)


# --- misc functions ---
def process_sample(now: float, then: float) -> None:

    detector.new_sample(sample=icm.gyro[SAMPLE_INDEX], dt=now - then)


def readline():
    if not USE_BLUETOOTH:
        return None
    else:
        uart.readline()


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


# --- buisness logic ---
def main():
    print("starting advertising...")
    wait_for_connection(run_samples=False)

    print("please close the door, the device will calibrate itself in 5 seconds...")
    for left in range(1, 5, -1):
        print(f"{left}...")
        time.sleep(1)
    else:
        detector.calibrate()

    while True:
        main_loop()


last_time = time.monotonic()


def main_loop():
    global last_time
    now = time.monotonic()

    if not ble.connected and USE_BLUETOOTH:
        print("disconnected")
        wait_for_connection()  # no timeout
        print(f"door used X times, left open Y times")
    # read from the UART and dispatch to the appropriate handler (if any)
    elif (msg := readline()) is not None:
        print("got msg:", repr(msg))
    else:
        pass

    process_sample(then=last_time, now=now)

    last_time = now
    time.sleep(LOOP_SLEEP_TIME)


if __name__ == "__main__":

    main()
