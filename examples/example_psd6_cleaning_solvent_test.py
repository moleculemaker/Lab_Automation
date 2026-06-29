# PSD/6 25 mL cleaning solvent test
# run from repo root with:
#   python -m examples.example_psd6_cleaning_solvent_test

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
CLEANING_SOLVENT_TEST_VOLUME_UL = 15_000.0
RESERVOIR_DRAIN_REPEATS = 3

PORT_SONICATOR_RESERVOIR = 1
PORT_IPA = 2
PORT_ACETONE = 3
PORT_TOLUENE = 4
PORT_AIR_EMPTY = 5
PORT_WASTE = 6
PORT_SAFE_IDLE = PORT_AIR_EMPTY

CLEANING_SOLVENT_PORTS = [
    (PORT_IPA, "IPA"),
    (PORT_ACETONE, "acetone"),
    (PORT_TOLUENE, "toluene"),
]


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
    print("Hamilton PSD/6 25 mL cleaning solvent test")
    print(f"- Port: {PORT}")
    print(f"- Reservoir valve: {PORT_SONICATOR_RESERVOIR} / sonicator reservoir")
    print(f"- Waste valve: {PORT_WASTE}")
    print(
        f"- Reservoir drain: {RESERVOIR_DRAIN_REPEATS} transfers of "
        f"{CLEANING_SOLVENT_TEST_VOLUME_UL / 1000.0:.1f} mL from valve {PORT_SONICATOR_RESERVOIR} to valve {PORT_WASTE}"
    )
    print(f"- Cleaning solvent test volume: {CLEANING_SOLVENT_TEST_VOLUME_UL / 1000.0:.1f} mL")
    print(f"- Flowrate: {DEFAULT_FLOWRATE_UL_S / 1000.0:.1f} mL/s")
    print("- Known cleaning solvent ports:")
    for solvent_port, solvent_name in CLEANING_SOLVENT_PORTS:
        print(f"  - valve {solvent_port}: {solvent_name}")

    confirm = input(
        f"This will initialize COM17, drain valve {PORT_SONICATOR_RESERVOIR} to valve {PORT_WASTE} "
        f"{RESERVOIR_DRAIN_REPEATS} times, then transfer {CLEANING_SOLVENT_TEST_VOLUME_UL / 1000.0:.1f} mL each from valves 2, 3, and 4 "
        f"to valve {PORT_SONICATOR_RESERVOIR}. "
        "Type 'y' to continue: "
    ).strip().lower()
    if confirm != "y":
        print("Cleaning solvent test cancelled.")
        return

    pump = PSD6SyringePump(
        name="psd6_25ml_cleaning_solvent",
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
        print(f"connect: {ok} | {message}", flush=True)
        if not ok:
            return

        ok, message = pump.initialize()
        print(f"initialize: {ok} | {message}", flush=True)
        if not ok:
            return

        ok, message = pump.move_valve_position(PORT_SAFE_IDLE)
        print(f"safe idle move to valve {PORT_SAFE_IDLE}: {ok} | {message}", flush=True)
        if not ok:
            return

        for drain_idx in range(RESERVOIR_DRAIN_REPEATS):
            label = f"reservoir drain {PORT_SONICATOR_RESERVOIR}->{PORT_WASTE} {drain_idx + 1}/{RESERVOIR_DRAIN_REPEATS}"
            ok, message = pump.move_syringe_absolute_volume(
                0.0,
                valve_num=PORT_SONICATOR_RESERVOIR,
                flowrate=DEFAULT_FLOWRATE_UL_S,
            )
            print(f"{label} | reset to 0 uL on valve {PORT_SONICATOR_RESERVOIR}: {ok} | {message}", flush=True)
            if not ok:
                return

            ok = transfer_volume(
                pump,
                source_port=PORT_SONICATOR_RESERVOIR,
                dest_port=PORT_WASTE,
                volume_ul=CLEANING_SOLVENT_TEST_VOLUME_UL,
                flowrate_ul_s=DEFAULT_FLOWRATE_UL_S,
                label=label,
            )
            if not ok:
                return

        for solvent_port, solvent_name in CLEANING_SOLVENT_PORTS:
            label = f"{solvent_name} {CLEANING_SOLVENT_TEST_VOLUME_UL / 1000.0:.1f} mL transfer {solvent_port}->{PORT_SONICATOR_RESERVOIR}"
            ok, message = pump.move_syringe_absolute_volume(
                0.0,
                valve_num=solvent_port,
                flowrate=DEFAULT_FLOWRATE_UL_S,
            )
            print(f"{label} | reset to 0 uL on valve {solvent_port}: {ok} | {message}", flush=True)
            if not ok:
                return

            ok = transfer_volume(
                pump,
                source_port=solvent_port,
                dest_port=PORT_SONICATOR_RESERVOIR,
                volume_ul=CLEANING_SOLVENT_TEST_VOLUME_UL,
                flowrate_ul_s=DEFAULT_FLOWRATE_UL_S,
                label=label,
            )
            if not ok:
                return

        valve_position = pump.valve_position()
        print(f"reported valve position: {valve_position}", flush=True)
    finally:
        if pump.ser.is_open and pump._is_initialized:
            idle_ok, idle_message = pump.move_valve_position(PORT_SAFE_IDLE)
            print(f"pre-deinitialize safe idle move to valve {PORT_SAFE_IDLE}: {idle_ok} | {idle_message}", flush=True)
        deinit_ok, deinit_message = pump.deinitialize(reset_init_flag=True)
        print(f"deinitialize: {deinit_ok} | {deinit_message}", flush=True)
        if pump.ser.is_open:
            pump.ser.close()
            print("serial: closed", flush=True)


if __name__ == "__main__":
    main()
