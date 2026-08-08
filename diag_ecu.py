"""
diag_ecu.py
-----------
Diagnostic ECU / responder.

Supports:
    0x19 -> Read Diagnostic Trouble Codes
    0x14 -> Clear Diagnostic Trouble Codes

The Diagnostic ECU receives the Engine ECU's diagnostic
status on 0x101.

For Clear DTC, it sends:
    CAN ID 0x102
    Data 01

to the Engine ECU.
"""

import time
import random
import can

from bus_config import get_bus
from signal_map import (
    DIAG_REQUEST_ID,
    DIAG_RESPONSE_ID,
    DIAG_STATUS_ID,
    ENGINE_COMMAND_ID,
    READ_DTC_SERVICE,
    CLEAR_DTC_SERVICE,
    decode_diag_request,
    encode_diag_response_positive,
    encode_diag_response_negative,
)


# UDS Negative Response Code
# 0x11 = Service Not Supported
NEGATIVE_RESPONSE_CODE = 0x11

# Latest DTC information received from Engine ECU
stored_dtcs = []


def update_dtcs(diag_byte):
    """
    Decode the diagnostic status byte received
    from the Engine ECU.

    Bit 0 -> P0217
    Bit 1 -> P0219
    """

    global stored_dtcs

    stored_dtcs = []

    if diag_byte & 0x01:
        stored_dtcs.append(0x0217)

    if diag_byte & 0x02:
        stored_dtcs.append(0x0219)


def send_clear_command(bus):
    """
    Send Clear DTC command to Engine ECU.

    CAN ID 0x102
    Data 01
    """

    clear_msg = can.Message(
        arbitration_id=ENGINE_COMMAND_ID,
        data=bytes([0x01]),
        is_extended_id=False,
    )

    bus.send(clear_msg)

    print(
        "[diag_ecu] sent Engine ECU command "
        "-> CLEAR DTC (0x102, data=01)"
    )


def main():

    bus = get_bus()

    print(
        f"[diag_ecu] listening for diagnostic requests "
        f"on 0x{DIAG_REQUEST_ID:X}"
    )

    print(
        f"[diag_ecu] monitoring Engine diagnostic status "
        f"on 0x{DIAG_STATUS_ID:X}"
    )

    try:

        while True:

            # Receive CAN message
            msg = bus.recv(timeout=1.0)

            if msg is None:
                continue

            # =================================================
            # 1. Engine ECU diagnostic status
            # =================================================

            if msg.arbitration_id == DIAG_STATUS_ID:

                update_dtcs(msg.data[0])

                print(
                    f"[diag_ecu] Engine DTC status updated "
                    f"-> {stored_dtcs}"
                )

                continue

            # =================================================
            # 2. Ignore unrelated CAN messages
            # =================================================

            if msg.arbitration_id != DIAG_REQUEST_ID:
                continue

            # =================================================
            # 3. Decode diagnostic request
            # =================================================

            req = decode_diag_request(msg.data)

            service_id = req["service_id"]

            print(
                f"[diag_ecu] received request "
                f"-> SID=0x{service_id:02X}"
            )

            time.sleep(0.3)

            # =================================================
            # 4. READ DTC - Service 0x19
            # =================================================

            if service_id == READ_DTC_SERVICE:

                # Simulate occasional ECU busy condition
                if random.random() < 0.15:

                    resp_data = encode_diag_response_negative(
                        service_id,
                        NEGATIVE_RESPONSE_CODE,
                    )

                    print(
                        "[diag_ecu] responding NEGATIVE "
                        "(busy/not ready)"
                    )

                else:

                    resp_data = encode_diag_response_positive(
                        READ_DTC_SERVICE,
                        stored_dtcs,
                    )

                    print(
                        f"[diag_ecu] responding POSITIVE "
                        f"-> DTCs={stored_dtcs}"
                    )

            # =================================================
            # 5. CLEAR DTC - Service 0x14
            # =================================================

            elif service_id == CLEAR_DTC_SERVICE:

                print(
                    "[diag_ecu] Clear DTC request received"
                )

                # Tell Engine ECU to clear its stored DTC memory
                send_clear_command(bus)

                # Clear our local copy too.
                stored_dtcs.clear()

                # Positive response:
                # 0x14 + 0x40 = 0x54
                resp_data = bytes([0x54])

                print(
                    "[diag_ecu] responding POSITIVE "
                    "-> DTC memory cleared"
                )

            # =================================================
            # 6. Unsupported service
            # =================================================

            else:

                resp_data = encode_diag_response_negative(
                    service_id,
                    NEGATIVE_RESPONSE_CODE,
                )

                print(
                    "[diag_ecu] responding NEGATIVE "
                    f"(unsupported SID=0x{service_id:02X})"
                )

            # =================================================
            # 7. Send diagnostic response
            # =================================================

            resp_msg = can.Message(
                arbitration_id=DIAG_RESPONSE_ID,
                data=resp_data,
                is_extended_id=False,
            )

            bus.send(resp_msg)

    except KeyboardInterrupt:

        print("\n[diag_ecu] stopped.")

    finally:

        bus.shutdown()


if __name__ == "__main__":
    main()
