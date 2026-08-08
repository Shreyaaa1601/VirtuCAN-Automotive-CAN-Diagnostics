"""
listener.py
------------
CAN bus monitor.

Decodes:
- Engine status
- Brake status
- Diagnostic status
- Engine commands
- Diagnostic responses

Also logs all CAN traffic to can_log.csv.
"""

import csv
import time
import can

from bus_config import get_bus
from signal_map import (
    DECODERS,
    ENGINE_ID,
    BRAKE_ID,
    DIAG_STATUS_ID,
    ENGINE_COMMAND_ID,
)


LOG_FILE = "can_log.csv"
STALE_THRESHOLD_SEC = 3.0


KNOWN_NODES = {
    ENGINE_ID: "Engine ECU",
    BRAKE_ID: "Brake ECU",
    DIAG_STATUS_ID: "Engine Diagnostic Status",
}


def decode_diag_status(data):
    """Decode CAN ID 0x101 diagnostic status."""

    if not data:
        return "No diagnostic status data"

    status = data[0]

    dtcs = []

    if status & 0x01:
        dtcs.append("P0217")

    if status & 0x02:
        dtcs.append("P0219")

    if not dtcs:
        return {
            "type": "diagnostic_status",
            "dtcs": [],
            "status": "No faults"
        }

    return {
        "type": "diagnostic_status",
        "dtcs": dtcs,
        "status": "Fault(s) detected"
    }


def decode_engine_command(data):
    """Decode CAN ID 0x102 engine command."""

    if not data:
        return "No command data"

    command = data[0]

    if command == 0x01:
        return {
            "type": "engine_command",
            "command": "CLEAR_DTC"
        }

    return {
        "type": "engine_command",
        "command": f"UNKNOWN_0x{command:02X}"
    }


def main():

    bus = get_bus()

    print(
        "[listener] listening for CAN traffic... "
        "(Ctrl+C to stop)\n"
    )

    last_seen = {}
    last_warned = set()

    with open(LOG_FILE, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "timestamp",
                "can_id_hex",
                "dlc",
                "data_hex",
                "decoded",
            ]
        )

        try:

            while True:

                msg = bus.recv(timeout=1.0)

                now = time.time()

                if msg is not None:

                    last_seen[msg.arbitration_id] = now
                    last_warned.discard(msg.arbitration_id)

                    # -----------------------------------------
                    # Determine decoder
                    # -----------------------------------------

                    if msg.arbitration_id == DIAG_STATUS_ID:

                        decoded = decode_diag_status(msg.data)

                    elif msg.arbitration_id == ENGINE_COMMAND_ID:

                        decoded = decode_engine_command(msg.data)

                    else:

                        decoder = DECODERS.get(
                            msg.arbitration_id
                        )

                        decoded = (
                            decoder(msg.data)
                            if decoder
                            else None
                        )

                    # -----------------------------------------
                    # Display
                    # -----------------------------------------

                    ts = time.strftime("%H:%M:%S")

                    data_hex = msg.data.hex()

                    if decoded is not None:

                        print(
                            f"[{ts}] "
                            f"ID=0x{msg.arbitration_id:03X} "
                            f"raw={data_hex} "
                            f"-> {decoded}"
                        )

                    else:

                        print(
                            f"[{ts}] "
                            f"ID=0x{msg.arbitration_id:03X} "
                            f"raw={data_hex} "
                            f"-> (unknown ID)"
                        )

                    # -----------------------------------------
                    # CSV logging
                    # -----------------------------------------

                    writer.writerow(
                        [
                            ts,
                            f"0x{msg.arbitration_id:03X}",
                            msg.dlc,
                            data_hex,
                            decoded,
                        ]
                    )

                    f.flush()

                # ---------------------------------------------
                # ECU alive monitoring
                # ---------------------------------------------

                for node_id, name in KNOWN_NODES.items():

                    seen_at = last_seen.get(node_id)

                    if seen_at is None:
                        continue

                    if (
                        now - seen_at > STALE_THRESHOLD_SEC
                        and node_id not in last_warned
                    ):

                        print(
                            f"  !!! WARNING: {name} "
                            f"(0x{node_id:03X}) has gone silent "
                            f"for {STALE_THRESHOLD_SEC:.0f}s+ "
                            f"- possible failure !!!"
                        )

                        last_warned.add(node_id)

        except KeyboardInterrupt:

            print(
                "\n[listener] stopped. "
                f"Log saved to {LOG_FILE}"
            )

        finally:

            bus.shutdown()


if __name__ == "__main__":
    main()
