"""
ecu_brake.py
-------------
Simulates a "Brake ECU" node. Notice this uses CAN ID 0x200, a HIGHER
numeric value than the engine's 0x100.

Concept - Arbitration: in real CAN, LOWER ID = HIGHER priority. If two nodes
try to transmit at the exact same instant, the node with the lower ID wins
the bus (its dominant bits overwrite the other's recessive bits during the
arbitration phase) and the other node automatically backs off and retries.
So in our setup, if the engine and brake nodes ever collide, the engine
frame (0x100) always wins over the brake frame (0x200). This is one of the
things you can go and verify later with candump timestamps.
"""

import time
import random
import can

from bus_config import get_bus
from signal_map import BRAKE_ID, encode_brake_frame

def main():
    bus = get_bus()
    print(f"[ecu_brake] started, broadcasting ID 0x{BRAKE_ID:X} on the bus...")

    try:
        while True:
            # Randomly simulate the driver braking sometimes
            if random.random() < 0.3:
                pressure = random.uniform(20, 90)
                active = True
            else:
                pressure = 0
                active = False

            data = encode_brake_frame(pressure, active)
            msg = can.Message(
                arbitration_id=BRAKE_ID,
                data=data,
                is_extended_id=False,
            )
            bus.send(msg)
            print(f"[ecu_brake] sent -> pressure={pressure:.0f}% active={active}")

            time.sleep(0.7)
    except KeyboardInterrupt:
        print("\n[ecu_brake] stopped.")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
