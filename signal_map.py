"""
signal_map.py
--------------
This is our "mini-DBC" - defines what each CAN ID means and how its bytes
are packed. Now includes simplified UDS-style diagnostic messages using
REAL industry-standard OBD-II diagnostic IDs.

ID 0x100 - ENGINE STATUS
  byte 0-1 : RPM_raw        -> RPM = RPM_raw * 0.25
  byte 2   : Speed_kmh
  byte 3   : CoolantTemp_raw -> Temp(C) = CoolantTemp_raw - 40

ID 0x101 - ENGINE DIAGNOSTIC STATUS
  bit0 : P0217 (Engine Over Temperature)
  bit1 : P0219 (Engine Overspeed)

ID 0x102 - ENGINE COMMAND
  byte0 = 0x01 -> Clear Stored DTCs

ID 0x200 - BRAKE STATUS
  byte0 : BrakePressure_raw -> Pressure(%) = Pressure_raw * (100/255)
  byte1 : BrakeActive

ID 0x7DF - DIAGNOSTIC REQUEST
  byte0 : Service ID (SID)

ID 0x7E8 - DIAGNOSTIC RESPONSE
  Positive : SID + 0x40
  Negative : 0x7F
"""

import struct

# -------------------------
# CAN IDs
# -------------------------
ENGINE_ID = 0x100
DIAG_STATUS_ID = 0x101
ENGINE_COMMAND_ID = 0x102
BRAKE_ID = 0x200

DIAG_REQUEST_ID = 0x7DF
DIAG_RESPONSE_ID = 0x7E8

# -------------------------
# Diagnostic Services
# -------------------------
READ_DTC_SERVICE = 0x19
CLEAR_DTC_SERVICE = 0x14

# -------------------------
# Engine Encoding
# -------------------------
def encode_engine_frame(rpm: float, speed_kmh: int, coolant_temp_c: int) -> bytes:
    rpm_raw = int(rpm / 0.25)
    rpm_raw = max(0, min(rpm_raw, 0xFFFF))

    speed_kmh = max(0, min(speed_kmh, 255))

    temp_raw = coolant_temp_c + 40
    temp_raw = max(0, min(temp_raw, 255))

    return struct.pack(">HBB", rpm_raw, speed_kmh, temp_raw)


def decode_engine_frame(data: bytes) -> dict:
    rpm_raw, speed_kmh, temp_raw = struct.unpack(">HBB", data[:4])

    return {
        "rpm": round(rpm_raw * 0.25, 2),
        "speed_kmh": speed_kmh,
        "coolant_temp_c": temp_raw - 40,
    }


# -------------------------
# Brake Encoding
# -------------------------
def encode_brake_frame(pressure_percent: float, active: bool) -> bytes:
    pressure_raw = int(pressure_percent * (255 / 100))
    pressure_raw = max(0, min(pressure_raw, 255))

    return struct.pack(">BB", pressure_raw, int(active))


def decode_brake_frame(data: bytes) -> dict:
    pressure_raw, active = struct.unpack(">BB", data[:2])

    return {
        "brake_pressure_percent": round(pressure_raw * (100 / 255), 1),
        "brake_active": bool(active),
    }


# -------------------------
# DTC Formatting
# -------------------------
def format_dtc(raw16: int) -> str:
    category_map = {
        0b00: "P",
        0b01: "C",
        0b10: "B",
        0b11: "U",
    }

    category = category_map[(raw16 >> 14) & 0b11]
    code_num = raw16 & 0x3FFF

    return f"{category}{code_num:04X}"


# -------------------------
# Diagnostic Messages
# -------------------------
def encode_diag_request(service_id: int) -> bytes:
    return bytes([service_id])


def decode_diag_request(data: bytes) -> dict:
    return {"service_id": data[0]}


def encode_diag_response_positive(service_id: int, dtc_list: list) -> bytes:
    body = bytes([service_id + 0x40, len(dtc_list)])

    for dtc in dtc_list:
        body += struct.pack(">H", dtc)

    return body


def encode_diag_response_negative(service_id: int, nrc: int) -> bytes:
    return bytes([0x7F, service_id, nrc])


def decode_diag_response(data: bytes) -> dict:

    # -----------------------------------------
    # Invalid / empty response
    # -----------------------------------------
    if len(data) == 0:
        return {
            "type": "invalid",
            "error": "Empty diagnostic response",
        }

    # -----------------------------------------
    # Negative response
    # Format:
    # 7F | requested SID | NRC
    # -----------------------------------------
    if data[0] == 0x7F:

        if len(data) < 3:
            return {
                "type": "invalid",
                "error": "Incomplete negative response",
            }

        return {
            "type": "negative",
            "requested_service": data[1],
            "nrc": data[2],
        }

    # -----------------------------------------
    # Clear DTC positive response
    # 0x54 = 0x14 + 0x40
    # -----------------------------------------
    if data[0] == 0x54:

        return {
            "type": "positive",
            "response_sid": 0x54,
            "service": 0x14,
            "dtc_count": 0,
            "dtcs": [],
            "operation": "clear_dtc",
        }

    # -----------------------------------------
    # Read DTC positive response
    # Format:
    # response SID | DTC count | DTC1 | DTC2...
    # -----------------------------------------
    if len(data) < 2:

        return {
            "type": "invalid",
            "error": "Incomplete positive response",
        }

    sid = data[0]
    count = data[1]

    dtcs = []

    for i in range(count):

        start = 2 + i * 2
        end = start + 2

        if end > len(data):
            return {
                "type": "invalid",
                "error": "Incomplete DTC data",
            }

        raw = struct.unpack(
            ">H",
            data[start:end]
        )[0]

        dtcs.append(format_dtc(raw))

    return {
        "type": "positive",
        "response_sid": sid,
        "dtc_count": count,
        "dtcs": dtcs,
        "operation": "read_dtc",
    }

# -------------------------
# Listener Decoders
# -------------------------
DECODERS = {
    ENGINE_ID: decode_engine_frame,
    BRAKE_ID: decode_brake_frame,
    DIAG_RESPONSE_ID: decode_diag_response,
}
