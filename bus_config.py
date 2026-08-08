"""
bus_config.py
--------------
Centralizes how we connect to the CAN bus, so every script (ecu_engine.py,
ecu_brake.py, listener.py) opens the bus the exact same way.

Two modes, controlled by an environment variable:

  CAN_MODE=socketcan  (default when you're on real Linux with vcan0 set up)
      -> connects to the real SocketCAN interface named by CAN_CHANNEL (vcan0)

  CAN_MODE=virtual    (use this if you're testing without SocketCAN,
                        e.g. inside this sandbox, or on Windows/Mac)
      -> uses python-can's in-process "virtual" bus. Multiple Bus() objects
         that use the same channel name, in the same process/threads, will
         see each other's messages. Good enough to prove the logic works,
         but it's NOT a substitute for real vcan0 - use socketcan on your
         actual machine for the "real" learning experience.
"""

import os
import can

CAN_MODE = os.environ.get("CAN_MODE", "socketcan")   # socketcan | virtual
CAN_CHANNEL = os.environ.get("CAN_CHANNEL", "vcan0")


def get_bus():
    if CAN_MODE == "virtual":
        return can.interface.Bus(channel=CAN_CHANNEL, interface="virtual")
    else:
        return can.interface.Bus(channel=CAN_CHANNEL, interface="socketcan")
