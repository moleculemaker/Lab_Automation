# PSD/6 1 mL port 1 transfer check
# run from repo root with:
#   python -m examples.example_psd6_1ml_suction_test

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from devices.psd6_syringe_pump import PSD6SyringePump


PORT = "COM14"
STROKE_VOLUME_UL = 1_000.0
AIR_PURGE_FLOWRATE_UL_S = 5.0
LOAD_FLOWRATE_UL_S = 10.0
PURGE_FLOWRATE_UL_S = 10.0
DISPENSE_FLOWRATE_UL_S = 10.0
AIR_SOURCE_PORT = 5
SOURCE_PORT = 1
DEST_PORT = 6
AIR_PURGE_VOLUME_UL = 100.0
LOAD_VOLUME_UL = 1_000.0
FIRST_PURGE_VOLUME_UL = 700.0
RELOAD_VOLUME_UL = 300.0
SECOND_PURGE_VOLUME_UL = 500.0
EXPECTED_REMAINING_VOLUME_UL = (
    LOAD_VOLUME_UL - FIRST_PURGE_VOLUME_UL + RELOAD_VOLUME_UL - SECOND_PURGE_VOLUME_UL
)


def transfer_volume(
    pump: PSD6SyringePump,
    source_port: int,
    dest_port: int,
    volume_ul: float,
    flowrate_ul_s: float,
    label: str,
) -> bool:
    ok, message = pump.withdraw_syringe_volume(
        volume_ul,
        valve_num=source_port,
        flowrate=flowrate_ul_s,
    )
    print(f"{label} | withdraw from valve {source_port}: {ok} | {message}", flush=True)
    if not ok:
        return False

    ok, message = pump.infuse_syringe_volume(
        volume_ul,
        valve_num=dest_port,
        flowrate=flowrate_ul_s,
    )
    print(f"{label} | infuse to valve {dest_port}: {ok} | {message}", flush=True)
    return ok


def main() -> None:
    print("Hamilton PSD/6 1 mL port 1 automatic loading check")
    print(f"- Port: {PORT}")
    print("- Syringe: 1 mL")
    print(f"- Air source valve: {AIR_SOURCE_PORT}")
    print(f"- Source valve: {SOURCE_PORT} / liquid handler")
    print(f"- Destination valve: {DEST_PORT}")
    print("- Purpose: air-purge port 1, wet/load the liquid-handler line, and finish with 100 uL nominally loaded.")
    print(f"- Air purge flowrate: {AIR_PURGE_FLOWRATE_UL_S:.1f} uL/s")
    print(f"- Load flowrate: {LOAD_FLOWRATE_UL_S:.1f} uL/s")
    print(f"- Liquid-handler purge flowrate: {PURGE_FLOWRATE_UL_S:.1f} uL/s")
    print(f"- Interactive dispense flowrate: {DISPENSE_FLOWRATE_UL_S:.1f} uL/s")
    print(f"- Air purge: {AIR_PURGE_VOLUME_UL:.0f} uL from valve {AIR_SOURCE_PORT} to valve {SOURCE_PORT}")
    print(f"- Load: withdraw {LOAD_VOLUME_UL:.0f} uL from valve {SOURCE_PORT}")
    print(f"- Wetting purge: infuse {FIRST_PURGE_VOLUME_UL:.0f} uL back to valve {SOURCE_PORT}")
    print(f"- Reload: withdraw {RELOAD_VOLUME_UL:.0f} uL from valve {SOURCE_PORT}")
    print(f"- Final purge: infuse {SECOND_PURGE_VOLUME_UL:.0f} uL back to valve {SOURCE_PORT}")
    print(f"- Expected final syringe load: {EXPECTED_REMAINING_VOLUME_UL:.0f} uL")

    confirm = input(
        f"This will connect to {PORT}, initialize the pump, air-purge {AIR_SOURCE_PORT}->{SOURCE_PORT}, "
        f"then run the automatic 1000/700/300/500 uL loading sequence. Type 'y' to continue: "
    ).strip().lower()
    if confirm != "y":
        print("Transfer check cancelled.")
        return

    pump = PSD6SyringePump(
        name="psd6_1ml_com14",
        port=PORT,
        baudrate=9600,
        timeout=10.0,
        stroke_volume=STROKE_VOLUME_UL,
        stroke_steps=6000,
        default_flowrate=LOAD_FLOWRATE_UL_S,
        port_dead_volumes=[0.0] * 6,
        poll_interval=0.1,
    )

    try:
        ok, message = pump.start_serial(delay=1.0)
        print(f"connect: {ok} | {message}")
        if not ok:
            return

        ok, message = pump.initialize()
        print(f"initialize: {ok} | {message}")
        if not ok:
            return

        ok, message = pump.move_syringe_absolute_volume(
            0.0,
            valve_num=AIR_SOURCE_PORT,
            flowrate=AIR_PURGE_FLOWRATE_UL_S,
        )
        print(f"reset to 0 uL on valve {AIR_SOURCE_PORT}: {ok} | {message}")
        if not ok:
            return

        ok = transfer_volume(
            pump,
            source_port=AIR_SOURCE_PORT,
            dest_port=SOURCE_PORT,
            volume_ul=AIR_PURGE_VOLUME_UL,
            flowrate_ul_s=AIR_PURGE_FLOWRATE_UL_S,
            label=f"air purge {AIR_SOURCE_PORT}->{SOURCE_PORT}",
        )
        if not ok:
            return

        pause_input = input(
            f"Air purge to valve {SOURCE_PORT} is complete. Check the liquid-handler line, then type 'y' to continue loading: "
        ).strip().lower()
        if pause_input != "y":
            print("Loading check cancelled after air purge.")
            return

        ok, message = pump.move_syringe_absolute_volume(
            0.0,
            valve_num=SOURCE_PORT,
            flowrate=LOAD_FLOWRATE_UL_S,
        )
        print(f"reset to 0 uL on valve {SOURCE_PORT}: {ok} | {message}")
        if not ok:
            return

        ok, message = pump.withdraw_syringe_volume(
            LOAD_VOLUME_UL,
            valve_num=SOURCE_PORT,
            flowrate=LOAD_FLOWRATE_UL_S,
        )
        print(f"load from valve {SOURCE_PORT}: {ok} | {message}")
        if not ok:
            return

        remaining_loaded_ul = LOAD_VOLUME_UL
        print(f"Nominal remaining syringe load: {remaining_loaded_ul:.0f} uL.")

        pause_input = input(
            f"Check whether {LOAD_VOLUME_UL:.0f} uL loaded from valve {SOURCE_PORT}, then type 'y' to run the 700/300/500 uL wetting sequence: "
        ).strip().lower()
        if pause_input != "y":
            print("Loading check stopped after full withdraw.")
            return

        ok, message = pump.infuse_syringe_volume(
            FIRST_PURGE_VOLUME_UL,
            valve_num=SOURCE_PORT,
            flowrate=PURGE_FLOWRATE_UL_S,
        )
        print(f"wetting purge to valve {SOURCE_PORT}: {ok} | {message}")
        if not ok:
            return
        remaining_loaded_ul -= FIRST_PURGE_VOLUME_UL
        print(f"Nominal remaining syringe load: {remaining_loaded_ul:.0f} uL.")

        ok, message = pump.withdraw_syringe_volume(
            RELOAD_VOLUME_UL,
            valve_num=SOURCE_PORT,
            flowrate=LOAD_FLOWRATE_UL_S,
        )
        print(f"reload from valve {SOURCE_PORT}: {ok} | {message}")
        if not ok:
            return
        remaining_loaded_ul += RELOAD_VOLUME_UL
        print(f"Nominal remaining syringe load: {remaining_loaded_ul:.0f} uL.")

        ok, message = pump.infuse_syringe_volume(
            SECOND_PURGE_VOLUME_UL,
            valve_num=SOURCE_PORT,
            flowrate=PURGE_FLOWRATE_UL_S,
        )
        print(f"final purge to valve {SOURCE_PORT}: {ok} | {message}")
        if not ok:
            return
        remaining_loaded_ul -= SECOND_PURGE_VOLUME_UL
        print(f"Nominal remaining syringe load: {remaining_loaded_ul:.0f} uL.")

        print(
            f"Interactive dispensing started. Enter a number in uL to dispense to valve {SOURCE_PORT}, or 'q' to stop."
        )
        while remaining_loaded_ul > 0.0:
            user_input = input(
                f"[{remaining_loaded_ul:.0f} uL nominal remaining] dispense uL to valve {SOURCE_PORT}: "
            ).strip().lower()

            if user_input in ("q", "quit", "exit"):
                print("Interactive dispensing stopped by user.")
                break

            try:
                dispense_ul = float(user_input)
            except ValueError:
                print("Invalid input. Enter a number in uL, or 'q' to stop.")
                continue

            if dispense_ul <= 0.0:
                print("Dispense volume must be greater than 0 uL.")
                continue
            if dispense_ul > remaining_loaded_ul:
                print(
                    f"Requested {dispense_ul:.0f} uL but only about {remaining_loaded_ul:.0f} uL remains."
                )
                continue

            ok, message = pump.infuse_syringe_volume(
                dispense_ul,
                valve_num=SOURCE_PORT,
                flowrate=DISPENSE_FLOWRATE_UL_S,
            )
            print(f"dispense to valve {SOURCE_PORT}: {ok} | {message}")
            if not ok:
                return

            remaining_loaded_ul -= dispense_ul
            print(f"Nominal remaining syringe load: {remaining_loaded_ul:.0f} uL.")

        if remaining_loaded_ul <= 0.0:
            print("Syringe nominally empty.")

        valve_position = pump.valve_position()
        print(f"reported valve position: {valve_position}")
        print(f"Automatic loading check finished. Syringe nominally holds about {remaining_loaded_ul:.0f} uL.")
    finally:
        deinit_ok, deinit_message = pump.deinitialize(reset_init_flag=True)
        print(f"deinitialize: {deinit_ok} | {deinit_message}")
        if pump.ser.is_open:
            pump.ser.close()
            print("serial: closed")


if __name__ == "__main__":
    main()
