# PSD/6 syringe pump smoke test
# run from repo root with:
#   python -m examples.example_psd6_syringe_pump

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from devices.psd6_syringe_pump import PSD6SyringePump


PORT = "COM17"
STROKE_VOLUME_UL = 25_000.0
DEFAULT_FLOWRATE_UL_S = 1_000.0
LARGE_TEST_VOLUME_UL = 24_000.0
PRIME_TEST_VOLUME_UL = 3_000.0
PORT_SONICATOR_RESERVOIR = 1
PORT_IPA = 2
PORT_AIR_EMPTY = 5
PORT_WASTE = 6
PORT_SAFE_IDLE = PORT_AIR_EMPTY


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
    print(f"{label} | withdraw from valve {source_port}: {ok} | {message}")
    if not ok:
        return False

    ok, message = pump.infuse_syringe_volume(
        volume_ul,
        valve_num=dest_port,
        flowrate=flowrate_ul_s,
    )
    print(f"{label} | infuse to valve {dest_port}: {ok} | {message}")
    return ok


def main() -> None:
    print("Hamilton PSD/6 smoke test")
    print(f"- Port: {PORT}")
    print("- Syringe: 25 mL")
    print("- Valve: 9998-01, 6-port distribution valve (positions 1-6)")
    print("- Tubing: 1/8 in downstream tubing is fine mechanically, but the Hamilton valve ports are still 1/4-28 fittings.")
    print("- Port map:")
    print(f"  - {PORT_SONICATOR_RESERVOIR}: sonicator reservoir")
    print(f"  - {PORT_IPA}: IPA")
    print(f"  - {PORT_AIR_EMPTY}: empty / air")
    print(f"  - {PORT_WASTE}: waste")
    print(f"- Large transfer volume is {LARGE_TEST_VOLUME_UL / 1000.0:.1f} mL.")
    print(f"- Prime test volume is {PRIME_TEST_VOLUME_UL / 1000.0:.1f} mL.")
    print(
        f"- The pump initializes with /1ZR, which homes the syringe and returns the valve to position 1, then this example moves it to safe idle port {PORT_SAFE_IDLE}."
    )

    confirm = input(
        "This will connect to COM17, move to safe idle 5, air-purge 5->2 three times at 24 mL, then prime 2->6 two times at 3 mL. Type 'y' to continue: "
    ).strip().lower()
    if confirm != "y":
        print("Smoke test cancelled.")
        return

    pump = PSD6SyringePump(
        name="psd6_com17",
        port=PORT,
        baudrate=9600,
        timeout=10.0,
        stroke_volume=STROKE_VOLUME_UL,
        stroke_steps=6000,
        default_flowrate=DEFAULT_FLOWRATE_UL_S,
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

        ok, message = pump.move_valve_position(PORT_SAFE_IDLE)
        print(f"post-initialize safe idle move to valve {PORT_SAFE_IDLE}: {ok} | {message}")
        if not ok:
            return

        # Reservoir drain template: keep this block here so it can be copied into
        # a recipe later when you want to empty the sonicator reservoir.
        # for drain_idx in range(3):
        #     label = f"reservoir drain {drain_idx + 1}/3"
        #     ok, message = pump.move_syringe_absolute_volume(
        #         0.0,
        #         valve_num=PORT_SONICATOR_RESERVOIR,
        #         flowrate=DEFAULT_FLOWRATE_UL_S,
        #     )
        #     print(f"{label} | reset to 0.0 mL on valve {PORT_SONICATOR_RESERVOIR}: {ok} | {message}")
        #     if not ok:
        #         return
        #
        #     ok = transfer_volume(
        #         pump,
        #         source_port=PORT_SONICATOR_RESERVOIR,
        #         dest_port=PORT_WASTE,
        #         volume_ul=LARGE_TEST_VOLUME_UL,
        #         flowrate_ul_s=DEFAULT_FLOWRATE_UL_S,
        #         label=label,
        #     )
        #     if not ok:
        #         return

        for purge_idx in range(3):
            label = f"air purge 5->2 {purge_idx + 1}/3"
            ok, message = pump.move_syringe_absolute_volume(
                0.0,
                valve_num=PORT_AIR_EMPTY,
                flowrate=DEFAULT_FLOWRATE_UL_S,
            )
            print(f"{label} | reset to 0.0 mL on valve {PORT_AIR_EMPTY}: {ok} | {message}")
            if not ok:
                return

            ok = transfer_volume(
                pump,
                source_port=PORT_AIR_EMPTY,
                dest_port=PORT_IPA,
                volume_ul=LARGE_TEST_VOLUME_UL,
                flowrate_ul_s=DEFAULT_FLOWRATE_UL_S,
                label=label,
            )
            if not ok:
                return

        for prime_idx in range(2):
            label = f"IPA prime 2->6 {prime_idx + 1}/2"
            ok, message = pump.move_syringe_absolute_volume(
                0.0,
                valve_num=PORT_IPA,
                flowrate=DEFAULT_FLOWRATE_UL_S,
            )
            print(f"{label} | reset to 0.0 mL on valve {PORT_IPA}: {ok} | {message}")
            if not ok:
                return

            ok = transfer_volume(
                pump,
                source_port=PORT_IPA,
                dest_port=PORT_WASTE,
                volume_ul=PRIME_TEST_VOLUME_UL,
                flowrate_ul_s=DEFAULT_FLOWRATE_UL_S,
                label=label,
            )
            if not ok:
                return

        valve_position = pump.valve_position()
        print(f"reported valve position: {valve_position}")
    finally:
        if pump.ser.is_open and pump._is_initialized:
            idle_ok, idle_message = pump.move_valve_position(PORT_SAFE_IDLE)
            print(f"pre-deinitialize safe idle move to valve {PORT_SAFE_IDLE}: {idle_ok} | {idle_message}")
        deinit_ok, deinit_message = pump.deinitialize(reset_init_flag=True)
        print(f"deinitialize: {deinit_ok} | {deinit_message}")
        if pump.ser.is_open:
            pump.ser.close()
            print("serial: closed")


if __name__ == "__main__":
    main()
