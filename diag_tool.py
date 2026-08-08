"""
diag_tool.py
------------
Simulates an automotive diagnostic scan tool.

Supports:
    1 -> Read DTCs (UDS Service 0x19)
    2 -> Clear DTCs (UDS Service 0x14)
"""

import time
import can

from bus_config import get_bus
from signal_map import (
    DIAG_REQUEST_ID,
    DIAG_RESPONSE_ID,
    READ_DTC_SERVICE,
    CLEAR_DTC_SERVICE,
    encode_diag_request,
    decode_diag_response,
)


def send_request(bus, service_id):
    """Send a diagnostic request to the Diagnostic ECU."""

    req_data = encode_diag_request(service_id)

    req_msg = can.Message(
        arbitration_id=DIAG_REQUEST_ID,
        data=req_data,
        is_extended_id=False,
    )

    bus.send(req_msg)

    print(
        f"\n[diag_tool] sent request "
        f"-> service=0x{service_id:02X}"
    )


def wait_for_response(bus):
    """Wait up to 2 seconds for a diagnostic response."""

    deadline = time.time() + 2.0

    while time.time() < deadline:

        remaining = deadline - time.time()

        msg = bus.recv(timeout=remaining)

        if msg is not None:
            if msg.arbitration_id == DIAG_RESPONSE_ID:
                return msg

    return None


def process_response(response):

    if response is None:

        print(
            "[diag_tool] !!! NO RESPONSE - "
            "Diagnostic ECU may be offline !!!"
        )

        return

    decoded = decode_diag_response(response.data)

    # -----------------------------
    # Positive response
    # -----------------------------

    if decoded["type"] == "positive":

        if decoded["dtc_count"] == 0:

            print(
                "[diag_tool] response: "
                "NO FAULT CODES STORED"
            )

        else:

            print(
                f"[diag_tool] response: "
                f"DTCs found -> {decoded['dtcs']}"
            )

    # -----------------------------
    # Negative response
    # -----------------------------

    else:

        print(
            f"[diag_tool] response: NEGATIVE "
            f"(NRC=0x{decoded['nrc']:02X})"
        )


def main():

    bus = get_bus()

    print("=" * 55)
    print("             VirtuCAN Diagnostic Tool")
    print("=" * 55)

    try:

        while True:

            print("\nDiagnostic Operations:")
            print("1. Read DTCs")
            print("2. Clear DTCs")
            print("3. Exit")

            choice = input("\nSelect operation: ").strip()

            # =============================================
            # Read DTC
            # =============================================

            if choice == "1":

                send_request(
                    bus,
                    READ_DTC_SERVICE
                )

                response = wait_for_response(bus)

                process_response(response)

            # =============================================
            # Clear DTC
            # =============================================

            elif choice == "2":

                print(
                    "\n[diag_tool] WARNING: "
                    "This will clear all stored DTCs."
                )

                confirm = input(
                    "Continue? (y/n): "
                ).strip().lower()

                if confirm == "y":

                    send_request(
                        bus,
                        CLEAR_DTC_SERVICE
                    )

                    response = wait_for_response(bus)

                    process_response(response)

                else:

                    print(
                        "[diag_tool] Clear operation cancelled."
                    )

            # =============================================
            # Exit
            # =============================================

            elif choice == "3":

                print(
                    "[diag_tool] exiting..."
                )

                break

            else:

                print(
                    "[diag_tool] Invalid choice."
                )

    except KeyboardInterrupt:

        print(
            "\n[diag_tool] stopped."
        )

    finally:

        bus.shutdown()


if __name__ == "__main__":
    main()
