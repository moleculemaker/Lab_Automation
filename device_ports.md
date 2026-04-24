# Device Ports

This file tracks the current local serial port assignments and related connection settings for lab hardware used in this repository.

## Notes

- Update this file when a device moves to a new port.
- If a port changes, update the related example, recipe, or web app configuration as needed.
- These values are machine-specific and may differ across lab PCs.

## Current Assignments

| Device Name | Model / Controller | Vendor | Port | Baudrate | Notes | Related Files |
| --- | --- | --- | --- | --- | --- | --- |
| `esp301_3n` | `ESP301-3N` with `axis1=ILS100CC`, `axis2=UTS100PP`, `axis3=PR50PP` | Newport | `COM6` | `921600` | Axis homing config: `OR4 / OR4 / OR1`; axis 3 is also used for the UV-Vis film degradation chamber workflow | `examples/example_esp301_3n.py`, `examples/example_uvvis_film_absorbance_degradation.py`, `recipes/recipe_sample.py`, `aamp_app/util.py` |
| `heater` | `HeatingStage` Arduino controller | Custom | `COM16` | `115200` | Smoke test updated locally; supports non-blocking setpoint command and explicit wait-for-temperature hold check | `examples/example_heating_stage.py`, `aamp_app/util.py`, `aamp_app/devices/heating_stage.py` |
| `linear_stage_150` | `LTS150` / `LinearStage150` | Thorlabs | `COM15` | `115200` | Smoke test updated locally to use `COM15`; initial absolute move tested at `100 mm` | `examples/example_linear_stage_150.py`, `aamp_app/util.py` |
| `z812` | `Z812` with `KDC101` | Thorlabs | `COM12` | `115200` | Smoke test passed locally with absolute move `8 mm` and relative move `3 mm` | `examples/example_z812.py`, `aamp_app/util.py`, `aamp_app/devices/z812.py` |
| `newport_94043a_solar_sim` | `94043A` solar simulator via `69920` power supply | Newport | `COM11` | `9600` | RS-232 via USB adapter; default control path is power mode; initialize applies `400 W` preset and software blocks presets above `450 W`; lamp replacement warning starts at `1000 h` | `examples/example_94043a_solar_sim.py`, `aamp_app/util.py`, `aamp_app/devices/newport_94043a_solar_sim.py` |
| `p4pp` | `P4PP` Arduino controller | PolyPrint Illinois | `COM19` | `115200` | Rotation is blocked when linear position is `>= 45.0 mm`; explicit measurement resistor selection supported with default `681 ohm`; measurement default cycles set to `20` | `examples/example_p4pp.py`, `aamp_app/util.py`, `aamp_app/devices/p4pp.py` |
| `apis` | `APIS` Arduino controller + Ximea camera | PolyPrint Illinois | `COM8` | `9600` | Composite device for stage control and imaging; default image root is `data/imaging/`; current example writes mode-organized outputs under `data/imaging/demo_campaign/` | `examples/example_apis.py`, `aamp_app/util.py`, `aamp_app/devices/apis.py` |
| `festo_valve` | `MHJ10-S-2,5-QS-1/4-MF-U` x2 via Arduino relay/driver wrapper | Festo + Custom | `COM9` | `9600` | Current local wiring uses Arduino `D8 -> valve_num=2` and `D4 -> valve_num=3`; companion sketch is `to_implement/festo_solenoid_valve_multiple/Festo_Multiple.ino`; valve supply is external `24 V DC`, `3-wire`, default closed/monostable | `examples/example_festo_solenoid_valve.py`, `aamp_app/devices/festo_solenoid_valve.py`, `aamp_app/commands/festo_solenoid_valve_commands.py`, `aamp_app/util.py`, `to_implement/festo_solenoid_valve_multiple/Festo_Multiple.ino` |
| `uhe_nl` | `UHE-NL 7 Sun` solar simulator power control | Sciencetech | `COM4` | `9600` | `initialize` requires lamp OFF and enables cooling first; lamp enable is blocked unless cooling feedback is on; `deinitialize` turns lamp off but leaves cooling on for cooldown | `examples/example_sciencetech_uhe_nl_solar_sim.py`, `aamp_app/util.py`, `aamp_app/devices/sciencetech_uhe_nl_solar_sim.py` |
| `stellarnet_uv_vis` | `StellarNet UV-Vis spectrometer` | StellarNet | `USB` | `n/a` | Vendor Python driver required in the environment; current local examples cover manual dark/blank/sample acquisition and ESP301-driven film degradation loops; spectral decay now uses `reference/am15g_spectrum.csv` | `examples/example_stellarnet_spectrometer.py`, `examples/example_uvvis_film_absorbance_degradation.py`, `aamp_app/devices/stellarnet_spectrometer.py` |
| `sonicator` | `Arduino Uno R3` wrapper for sonicator front-panel button/status lines | Custom | `COM13` | `9600` | Expected wiring is `5V`, `GND`, `D7` button drive, and `D8` status sense; Python smoke test passed locally; explicit power probe is intrusive and not used during initialize | `examples/example_sonicator.py`, `aamp_app/devices/sonicator.py`, `aamp_app/util.py`, `firmware/sonicator/sonicator_uno_r3/sonicator_uno_r3.ino` |
| `substrate_hotel` | `Arduino linear stage` for substrate hotel | Custom | `COM10` | `9600` | Current local assignment; protocol expects `Ready`, `H`, and `M{position},{speed}`; current Python guard range is `0-430 mm`; default homing and move timeouts are `300 s` | `examples/example_substrate_hotel.py`, `aamp_app/devices/substrate_hotel.py`, `aamp_app/util.py` |
| `substrate_dispenser` | `Arduino linear stage` for substrate dispenser | Custom | `COM7` | `9600` | Current local assignment; protocol expects `Ready`, `H`, and `M{position},{speed}`; current Python guard range is `0-45 mm` | `examples/example_substrate_dispenser.py`, `aamp_app/devices/substrate_dispenser.py`, `aamp_app/util.py` |

## Storage Notes

- `APIS` image outputs default to `data/imaging/`
- `P4PP` measurement CSV outputs default to `data/resistance/p4pp_measurements.csv`
- `StellarNetSpectrometer` outputs default to `data/spectroscopy/`
- StellarNet spectral-decay reference data is stored in `data/spectroscopy/reference/am15g_spectrum.csv`
- StellarNet repeated absorbance QC is appended to `sample_name_measurement_qc_log.csv` in `data/spectroscopy/`
