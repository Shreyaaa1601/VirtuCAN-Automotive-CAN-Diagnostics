"""
dashboard.py
------------
VirtuCAN Automotive CAN Dashboard

Reads live data from:
    0x100 -> Engine ECU
    0x101 -> Engine Diagnostic Status
    0x200 -> Brake ECU

Displays:
    - RPM
    - Speed
    - Coolant temperature
    - Brake pressure
    - Brake status
    - Active DTCs
    - ECU communication status
"""

import tkinter as tk
import threading
import time
import can

from bus_config import get_bus
from signal_map import (
    ENGINE_ID,
    DIAG_STATUS_ID,
    BRAKE_ID,
    decode_engine_frame,
    decode_brake_frame,
)


# ============================================================
# GLOBAL DATA
# ============================================================

data_lock = threading.Lock()

engine_data = {
    "rpm": 0,
    "speed_kmh": 0,
    "coolant_temp_c": 0,
}

brake_data = {
    "brake_pressure_percent": 0,
    "brake_active": False,
}

active_dtcs = []

last_engine_message = 0
last_brake_message = 0
last_diag_message = 0

running = True


# ============================================================
# CAN RECEIVER
# ============================================================

def can_receiver():
    global engine_data
    global brake_data
    global active_dtcs
    global last_engine_message
    global last_brake_message
    global last_diag_message
    global running

    bus = get_bus()

    print("[dashboard] CAN receiver started")

    try:
        while running:

            msg = bus.recv(timeout=1.0)

            if msg is None:
                continue

            now = time.time()

            # ------------------------------------------------
            # ENGINE STATUS - 0x100
            # ------------------------------------------------

            if msg.arbitration_id == ENGINE_ID:

                decoded = decode_engine_frame(msg.data)

                with data_lock:
                    engine_data = decoded
                    last_engine_message = now

            # ------------------------------------------------
            # ENGINE DIAGNOSTIC STATUS - 0x101
            # ------------------------------------------------

            elif msg.arbitration_id == DIAG_STATUS_ID:

                if len(msg.data) == 0:
                    continue

                status = msg.data[0]

                dtcs = []

                # Bit 0 -> P0217
                if status & 0x01:
                    dtcs.append("P0217")

                # Bit 1 -> P0219
                if status & 0x02:
                    dtcs.append("P0219")

                with data_lock:
                    active_dtcs = dtcs
                    last_diag_message = now

            # ------------------------------------------------
            # BRAKE STATUS - 0x200
            # ------------------------------------------------

            elif msg.arbitration_id == BRAKE_ID:

                decoded = decode_brake_frame(msg.data)

                with data_lock:
                    brake_data = decoded
                    last_brake_message = now

    except Exception as e:

        print(f"[dashboard] CAN error: {e}")

    finally:

        bus.shutdown()

        print("[dashboard] CAN receiver stopped")


# ============================================================
# DASHBOARD CLASS
# ============================================================

class Dashboard:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "VirtuCAN - Automotive CAN Dashboard"
        )

        self.root.geometry("1100x700")

        self.root.minsize(950, 600)

        self.root.configure(
            bg="#111111"
        )

        self.create_header()

        self.create_main_area()

        self.create_footer()

        self.update_dashboard()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )


    # ========================================================
    # HEADER
    # ========================================================

    def create_header(self):

        header = tk.Frame(
            self.root,
            bg="#1b1b1b",
            height=80
        )

        header.pack(
            fill="x",
            padx=10,
            pady=10
        )

        title = tk.Label(
            header,
            text="VirtuCAN",
            font=("Arial", 26, "bold"),
            bg="#1b1b1b",
            fg="white"
        )

        title.pack(
            side="left",
            padx=20,
            pady=15
        )

        subtitle = tk.Label(
            header,
            text="Automotive CAN Network Dashboard",
            font=("Arial", 12),
            bg="#1b1b1b",
            fg="#aaaaaa"
        )

        subtitle.pack(
            side="left",
            padx=5,
            pady=20
        )

        self.connection_label = tk.Label(
            header,
            text="● CAN CONNECTED",
            font=("Arial", 12, "bold"),
            bg="#1b1b1b",
            fg="#00ff88"
        )

        self.connection_label.pack(
            side="right",
            padx=20
        )


    # ========================================================
    # MAIN AREA
    # ========================================================

    def create_main_area(self):

        main = tk.Frame(
            self.root,
            bg="#111111"
        )

        main.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        # ----------------------------------------------------
        # ENGINE PANEL
        # ----------------------------------------------------

        engine_panel = self.create_panel(
            main,
            "ENGINE ECU"
        )

        engine_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=5,
            pady=5
        )

        self.rpm_value = self.create_value(
            engine_panel,
            "RPM"
        )

        self.speed_value = self.create_value(
            engine_panel,
            "SPEED"
        )

        self.temp_value = self.create_value(
            engine_panel,
            "COOLANT TEMPERATURE"
        )

        # ----------------------------------------------------
        # BRAKE PANEL
        # ----------------------------------------------------

        brake_panel = self.create_panel(
            main,
            "BRAKE ECU"
        )

        brake_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=5,
            pady=5
        )

        self.brake_value = self.create_value(
            brake_panel,
            "BRAKE PRESSURE"
        )

        self.brake_status = tk.Label(
            brake_panel,
            text="BRAKE INACTIVE",
            font=("Arial", 16, "bold"),
            bg="#1c1c1c",
            fg="#00ff88"
        )

        self.brake_status.pack(
            pady=20
        )

        # ----------------------------------------------------
        # DIAGNOSTICS PANEL
        # ----------------------------------------------------

        diag_panel = self.create_panel(
            main,
            "DIAGNOSTICS"
        )

        diag_panel.grid(
            row=0,
            column=2,
            sticky="nsew",
            padx=5,
            pady=5
        )

        self.dtc_title = tk.Label(
            diag_panel,
            text="ACTIVE DTCs",
            font=("Arial", 13, "bold"),
            bg="#1c1c1c",
            fg="#cccccc"
        )

        self.dtc_title.pack(
            pady=(15, 5)
        )

        self.dtc_list = tk.Listbox(
            diag_panel,
            font=("Courier New", 14, "bold"),
            bg="#111111",
            fg="#ff5555",
            bd=0,
            highlightthickness=0,
            height=6
        )

        self.dtc_list.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=10
        )

        # ----------------------------------------------------
        # NETWORK PANEL
        # ----------------------------------------------------

        network_panel = self.create_panel(
            main,
            "CAN NETWORK"
        )

        network_panel.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="nsew",
            padx=5,
            pady=5
        )

        # Use a separate frame for the network status
        # widgets. This avoids mixing pack() and grid()
        # inside the same parent.

        status_frame = tk.Frame(
            network_panel,
            bg="#1c1c1c"
        )

        status_frame.pack(
            fill="x",
            pady=10
        )

        self.engine_ecu_status = tk.Label(
            status_frame,
            text="ENGINE ECU     ● WAITING",
            font=("Arial", 13, "bold"),
            bg="#1c1c1c",
            fg="#ffaa00"
        )

        self.engine_ecu_status.pack(
            side="left",
            expand=True,
            padx=20
        )

        self.brake_ecu_status = tk.Label(
            status_frame,
            text="BRAKE ECU      ● WAITING",
            font=("Arial", 13, "bold"),
            bg="#1c1c1c",
            fg="#ffaa00"
        )

        self.brake_ecu_status.pack(
            side="left",
            expand=True,
            padx=20
        )

        self.diag_ecu_status = tk.Label(
            status_frame,
            text="DIAGNOSTIC ECU ● WAITING",
            font=("Arial", 13, "bold"),
            bg="#1c1c1c",
            fg="#ffaa00"
        )

        self.diag_ecu_status.pack(
            side="left",
            expand=True,
            padx=20
        )

        self.network_info = tk.Label(
            network_panel,
            text="CAN Bus: vcan0",
            font=("Arial", 12),
            bg="#1c1c1c",
            fg="#aaaaaa"
        )

        self.network_info.pack(
            pady=(0, 15)
        )

        # Make the main grid responsive

        main.columnconfigure(
            0,
            weight=1
        )

        main.columnconfigure(
            1,
            weight=1
        )

        main.columnconfigure(
            2,
            weight=1
        )

        main.rowconfigure(
            0,
            weight=3
        )

        main.rowconfigure(
            1,
            weight=1
        )


    # ========================================================
    # PANEL CREATION
    # ========================================================

    def create_panel(
        self,
        parent,
        title
    ):

        frame = tk.Frame(
            parent,
            bg="#1c1c1c",
            bd=1,
            relief="solid"
        )

        title_label = tk.Label(
            frame,
            text=title,
            font=("Arial", 15, "bold"),
            bg="#1c1c1c",
            fg="white"
        )

        title_label.pack(
            pady=(15, 5)
        )

        return frame


    # ========================================================
    # VALUE WIDGET
    # ========================================================

    def create_value(
        self,
        parent,
        name
    ):

        frame = tk.Frame(
            parent,
            bg="#1c1c1c"
        )

        frame.pack(
            fill="x",
            padx=15,
            pady=8
        )

        label = tk.Label(
            frame,
            text=name,
            font=("Arial", 10, "bold"),
            bg="#1c1c1c",
            fg="#999999"
        )

        label.pack()

        value = tk.Label(
            frame,
            text="--",
            font=("Arial", 26, "bold"),
            bg="#1c1c1c",
            fg="white"
        )

        value.pack()

        return value


    # ========================================================
    # FOOTER
    # ========================================================

    def create_footer(self):

        footer = tk.Frame(
            self.root,
            bg="#1b1b1b",
            height=35
        )

        footer.pack(
            fill="x",
            padx=10,
            pady=10
        )

        footer_label = tk.Label(
            footer,
            text="VirtuCAN | SocketCAN | vcan0",
            font=("Arial", 10),
            bg="#1b1b1b",
            fg="#777777"
        )

        footer_label.pack(
            pady=8
        )


    # ========================================================
    # UPDATE DASHBOARD
    # ========================================================

    def update_dashboard(self):

        with data_lock:

            current_engine = engine_data.copy()

            current_brake = brake_data.copy()

            current_dtcs = active_dtcs.copy()

            engine_time = last_engine_message

            brake_time = last_brake_message

            diag_time = last_diag_message

        now = time.time()

        # ----------------------------------------------------
        # ENGINE
        # ----------------------------------------------------

        self.rpm_value.config(
            text=f"{current_engine['rpm']:.0f}"
        )

        self.speed_value.config(
            text=f"{current_engine['speed_kmh']} km/h"
        )

        temperature = current_engine[
            "coolant_temp_c"
        ]

        self.temp_value.config(
            text=f"{temperature} °C"
        )

        # Temperature warning

        if temperature >= 100:

            self.temp_value.config(
                fg="#ff4444"
            )

        elif temperature >= 90:

            self.temp_value.config(
                fg="#ffaa00"
            )

        else:

            self.temp_value.config(
                fg="white"
            )

        # ----------------------------------------------------
        # BRAKE
        # ----------------------------------------------------

        pressure = current_brake[
            "brake_pressure_percent"
        ]

        self.brake_value.config(
            text=f"{pressure:.1f} %"
        )

        if current_brake["brake_active"]:

            self.brake_status.config(
                text="BRAKE ACTIVE",
                fg="#ff4444"
            )

        else:

            self.brake_status.config(
                text="BRAKE INACTIVE",
                fg="#00ff88"
            )

        # ----------------------------------------------------
        # DTCs
        # ----------------------------------------------------

        self.dtc_list.delete(
            0,
            tk.END
        )

        if current_dtcs:

            for dtc in current_dtcs:

                self.dtc_list.insert(
                    tk.END,
                    f"⚠  {dtc}"
                )

        else:

            self.dtc_list.insert(
                tk.END,
                "✓  NO ACTIVE DTCs"
            )

        # ----------------------------------------------------
        # ECU STATUS
        # ----------------------------------------------------

        engine_alive = (
            engine_time > 0
            and now - engine_time < 3
        )

        brake_alive = (
            brake_time > 0
            and now - brake_time < 3
        )

        diag_alive = (
            diag_time > 0
            and now - diag_time < 3
        )

        if engine_alive:

            self.engine_ecu_status.config(
                text="ENGINE ECU     ● ONLINE",
                fg="#00ff88"
            )

        else:

            self.engine_ecu_status.config(
                text="ENGINE ECU     ● OFFLINE",
                fg="#ff4444"
            )

        if brake_alive:

            self.brake_ecu_status.config(
                text="BRAKE ECU      ● ONLINE",
                fg="#00ff88"
            )

        else:

            self.brake_ecu_status.config(
                text="BRAKE ECU      ● OFFLINE",
                fg="#ff4444"
            )

        if diag_alive:

            self.diag_ecu_status.config(
                text="DIAGNOSTIC ECU ● ONLINE",
                fg="#00ff88"
            )

        else:

            self.diag_ecu_status.config(
                text="DIAGNOSTIC ECU ● WAITING",
                fg="#ffaa00"
            )

        # ----------------------------------------------------
        # CAN CONNECTION
        # ----------------------------------------------------

        if engine_alive or brake_alive:

            self.connection_label.config(
                text="● CAN CONNECTED",
                fg="#00ff88"
            )

        else:

            self.connection_label.config(
                text="● CAN WAITING",
                fg="#ffaa00"
            )

        # Update every 250 ms

        self.root.after(
            250,
            self.update_dashboard
        )


    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        global running

        running = False

        self.root.destroy()


# ============================================================
# MAIN
# ============================================================

def main():

    receiver_thread = threading.Thread(
        target=can_receiver,
        daemon=True
    )

    receiver_thread.start()

    root = tk.Tk()

    Dashboard(root)

    root.mainloop()


if __name__ == "__main__":

    main()
