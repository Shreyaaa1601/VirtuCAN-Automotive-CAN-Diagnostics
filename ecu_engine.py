"""
ecu_engine.py
--------------
Simulates an Engine ECU.

Responsibilities:
1. Broadcast engine data on CAN ID 0x100
2. Detect and store Diagnostic Trouble Codes (DTCs)
3. Broadcast diagnostic status on CAN ID 0x101
4. Listen for commands on CAN ID 0x102
5. Clear stored DTCs when command 0x01 is received
"""

import time
import random
import can

from bus_config import get_bus
from signal_map import (
    ENGINE_ID,
    DIAG_STATUS_ID,
    ENGINE_COMMAND_ID,
    encode_engine_frame,
)


def main():
    bus = get_bus()

    print(
        f"[ecu_engine] started, broadcasting "
        f"engine ID 0x{ENGINE_ID:X}"
    )

    # -----------------------------
    # Simulated engine parameters
    # -----------------------------
    rpm = 800.0
    speed = 0
    temp = 20.0

    # -----------------------------
    # Stored Diagnostic Trouble Codes
    # -----------------------------
    stored_dtcs = set()

    # Used to detect a NEW fault occurrence.
    # This prevents a cleared fault from immediately
    # returning while the condition is still present.
    previous_overtemp = False
    previous_overspeed = False

    try:

        while True:

            # =================================================
            # 1. Listen for commands from Diagnostic ECU
            # =================================================

            cmd = bus.recv(timeout=0.01)

            if cmd is not None:
                if cmd.arbitration_id == ENGINE_COMMAND_ID:

                    if len(cmd.data) > 0:

                        command = cmd.data[0]

                        # 0x01 = Clear all stored DTCs
                        if command == 0x01:

                            stored_dtcs.clear()

                            print(
                                "[ecu_engine] "
                                "DTC memory CLEARED"
                            )

            # =================================================
            # 2. Simulate engine behaviour
            # =================================================

            rpm += random.uniform(-100, 150)
            rpm = max(700, min(rpm, 6000))

            speed += random.randint(-2, 3)
            speed = max(0, min(speed, 180))

            temp += random.uniform(0, 1.5)
            temp = min(temp, 110)

            # =================================================
            # 3. Detect faults
            # =================================================

            current_overtemp = temp > 100
            current_overspeed = rpm > 5000

            # Detect transition into over-temperature condition
            if current_overtemp and not previous_overtemp:

                stored_dtcs.add("P0217")

                print(
                    "[ecu_engine] "
                    "FAULT DETECTED -> P0217 "
                    "(Engine Over Temperature)"
                )

            # Detect transition into overspeed condition
            if current_overspeed and not previous_overspeed:

                stored_dtcs.add("P0219")

                print(
                    "[ecu_engine] "
                    "FAULT DETECTED -> P0219 "
                    "(Engine Overspeed)"
                )

            previous_overtemp = current_overtemp
            previous_overspeed = current_overspeed

            # =================================================
            # 4. Broadcast normal Engine ECU message
            # =================================================

            data = encode_engine_frame(
                rpm,
                speed,
                int(temp)
            )

            engine_msg = can.Message(
                arbitration_id=ENGINE_ID,
                data=data,
                is_extended_id=False,
            )

            bus.send(engine_msg)

            # =================================================
            # 5. Broadcast Diagnostic Status
            #
            # 0x101
            #
            # bit 0 -> P0217
            # bit 1 -> P0219
            # =================================================

            diag_byte = 0x00

            if "P0217" in stored_dtcs:
                diag_byte |= 0x01

            if "P0219" in stored_dtcs:
                diag_byte |= 0x02

            diag_msg = can.Message(
                arbitration_id=DIAG_STATUS_ID,
                data=bytes([diag_byte]),
                is_extended_id=False,
            )

            bus.send(diag_msg)

            # =================================================
            # 6. Display current Engine ECU state
            # =================================================

            print(
                f"[ecu_engine] "
                f"RPM={rpm:.0f} "
                f"Speed={speed}km/h "
                f"Temp={temp:.0f}C "
                f"DTCs={list(stored_dtcs)}"
            )

            time.sleep(0.5)

    except KeyboardInterrupt:

        print("\n[ecu_engine] stopped.")

    finally:

        bus.shutdown()


if __name__ == "__main__":
    main()
