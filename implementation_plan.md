# Implementation Plan

This file tracks device and command work for this branch.

## Workflow

Use this order for each device:

1. Define scope and required actions
2. Implement device in `aamp_app/devices/`
3. Implement commands in `aamp_app/commands/`
4. Add or update an example in `examples/`
5. Run the example and confirm behavior
6. Check recipe or YAML compatibility if needed
7. Verify the device or commands appear correctly in the web app
8. Record follow-up issues

## Status Legend

- `planned`
- `in progress`
- `blocked`
- `done`

## Branch Summary

- Branch goal: add or update devices and commands, verify with examples, then confirm web app integration
- Owner: `TBD`
- Started: `2026-03-23`

## Device Tracking

### Device Template

Copy this section for each device and fill it in as work starts.

#### Device: `<name>`

- Status: `planned`
- Device file: `aamp_app/devices/<file>.py`
- Command file: `aamp_app/commands/<file>_commands.py`
- Example file: `examples/<example_name>.py`
- Similar existing implementation: `TBD`
- Hardware or SDK dependency: `TBD`

#### Scope

- Add:
- Update:
- Not in scope:

#### Required Actions

- [ ] Device class implemented
- [ ] Initialization path checked
- [ ] Shutdown or cleanup path checked
- [ ] Core commands implemented
- [ ] Command metadata and params reviewed
- [ ] Example added or updated
- [ ] Example executed successfully
- [ ] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [ ] Notes recorded

#### Validation

- Example run result:
- Web app result:
- Known issues:

#### Notes

- 

## Active Work Items

- [x] Device 1: `ESP301-3N`
- [x] Device 2: `Z812`
- [x] Device 3: `HeatingStage`
- [x] Device 4: `P4PP`
- [x] Device 5: `Sciencetech UHE-NL`
- [x] Device 6: `StellarNetSpectrometer`
- [x] Device 7: `Sonicator`
- [ ] Device 8: `SubstrateHotel`
- [ ] Device 9: `SubstrateDispenser`

#### Device: `ESP301-3N`

- Status: `in progress`
- Device file: `aamp_app/devices/newport_esp301.py`
- Command file: `aamp_app/commands/newport_esp301_commands.py`
- Example file: `examples/TBD`
- Similar existing implementation: `NewportESP301`, `LinearStage150`, `MTS50_Z8`
- Hardware or SDK dependency: `Newport ESP301-3N controller`

#### Scope

- Add: axis-type-aware initialization and homing behavior for `axis1=ILS100CC`, `axis2=UTS100PP`, `axis3=PR50PP`
- Update: existing `NewportESP301` device and related commands or metadata as needed
- Not in scope: unrelated non-ESP301 devices

#### Required Actions

- [ ] Confirm axis-specific home and initialization requirements
- [x] Device class updated
- [ ] Initialization path checked
- [ ] Shutdown or cleanup path checked
- [x] Core commands implemented or updated
- [x] Command metadata and params reviewed
- [ ] Example added or updated
- [ ] Example executed successfully
- [ ] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [ ] Notes recorded

#### Validation

- Example run result:
- Web app result:
- Known issues: web app visibility still not explicitly checked end-to-end

#### Notes

- Target hardware layout: `axis1=ILS100CC`, `axis2=UTS100PP`, `axis3=PR50PP`
- `NewportESP301` now supports `axis_configs` so each axis can declare `motion_type`, `units`, `home_mode`, `zero_position`, `default_speed`, and `max_speed`
- Validated homing policy: `OR4 / OR4 / OR1`
- Smoke test completed locally with axis-specific movement and re-home sequence

#### Device: `Z812`

- Status: `in progress`
- Device file: `aamp_app/devices/z812.py`
- Command file: `aamp_app/commands/z812_commands.py`
- Example file: `examples/example_z812.py`
- Similar existing implementation: `MTS50_Z8`, `LinearStage150`
- Hardware or SDK dependency: `Thorlabs KDC101 with Z812 actuator`

#### Scope

- Add: dedicated `Z812` device, commands, smoke test, and web app metadata
- Update: documentation and port tracking
- Not in scope: refactoring `MTS50_Z8` into a shared base class

#### Required Actions

- [x] Device class implemented
- [x] Initialization path checked
- [x] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [x] Example executed successfully
- [ ] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result: smoke test passed locally using `COM12`
- Web app result:
- Known issues: none reported yet

#### Notes

- Current local port assignment: `COM12`
- Smoke test sequence used `8 mm` absolute move, `3 mm` relative move, and return to `0 mm`

#### Device: `HeatingStage`

- Status: `done`
- Device file: `aamp_app/devices/heating_stage.py`
- Command file: `aamp_app/commands/heating_stage_commands.py`
- Example file: `examples/example_heating_stage.py`
- Similar existing implementation: `HeatingStage`
- Hardware or SDK dependency: `Heating stage Arduino controller`

#### Scope

- Add: explicit wait-for-temperature command with hold-time criterion
- Update: example and documentation with current port assignment
- Not in scope: heater firmware changes

#### Required Actions

- [x] Device class implemented
- [x] Initialization path checked
- [x] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [x] Example executed successfully
- [x] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result: smoke test executed locally on `COM16`
- Web app result:
- Known issues: none reported

#### Notes

- `HeatingStageSetSetPoint` is non-blocking
- `HeatingStageWaitForTemperature` now requires staying within tolerance for a hold duration before succeeding

#### Device: `P4PP`

- Status: `done`
- Device file: `aamp_app/devices/p4pp.py`
- Command file: `aamp_app/commands/p4pp_commands.py`
- Example file: `examples/example_p4pp.py`
- Similar existing implementation: external reference `changhwang/P4PP`
- Hardware or SDK dependency: `P4PP Arduino controller`

#### Scope

- Add: P4PP device, commands, smoke test, and web app metadata
- Update: safety and measurement configuration defaults
- Not in scope: firmware integration inside this repo

#### Required Actions

- [x] Device class implemented
- [x] Initialization path checked
- [x] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [x] Example executed successfully
- [x] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result: smoke test executed locally on `COM19`
- Web app result:
- Known issues: none reported

#### Notes

- Firmware and hardware details should reference `https://github.com/polyprintillinois/P4PP`
- Python behavior was aligned to the public driver in `https://github.com/changhwang/P4PP`
- Rotation is blocked when linear position is `>= 45.0 mm`
- Measurement resistor selection is explicit: `681 ohm` default, `68.1 ohm` optional
- Default measurement cycles for command metadata set to `20`

#### Device: `Sciencetech UHE-NL`

- Status: `done`
- Device file: `aamp_app/devices/sciencetech_uhe_nl_solar_sim.py`
- Command file: `aamp_app/commands/sciencetech_uhe_nl_solar_sim_commands.py`
- Example file: `examples/example_sciencetech_uhe_nl_solar_sim.py`
- Similar existing implementation: `to_implement/sciencetech_lamp.py`
- Hardware or SDK dependency: `Sciencetech UHE-NL / LPC controller over RS-232`

#### Scope

- Add: UHE-NL power control device, commands, smoke test, and web app metadata
- Update: safety handling for cooling and lamp sequencing
- Not in scope: optical calibration workflow

#### Required Actions

- [x] Device class implemented
- [x] Initialization path checked
- [x] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [x] Example executed successfully
- [x] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result: full smoke test executed locally on `COM4`
- Web app result:
- Known issues: controller reports `OUTPUT=0000` while the lamp is off even after a setpoint command; live output feedback becomes meaningful only after lamp ignition

#### Notes

- `initialize` requires the lamp to be off and enables cooling first
- `enable_arc_lamp` refuses to run unless cooling feedback is on
- `deinitialize` turns the lamp off when needed and intentionally leaves cooling on for cooldown

#### Device: `StellarNetSpectrometer`

- Status: `done`
- Device file: `aamp_app/devices/stellarnet_spectrometer.py`
- Command file: `aamp_app/commands/stellarnet_spectrometer_commands.py`
- Example file: `examples/example_stellarnet_spectrometer.py`, `examples/example_uvvis_film_absorbance_degradation.py`
- Similar existing implementation: existing StellarNet driver wrapper
- Hardware or SDK dependency: `stellarnet_driver3` and compatible `pyusb`

#### Scope

- Add: calibration/smoke test example for the UV-Vis spectrometer, by-name absorbance and photon-count acquisition, spectral-decay calculation, and an ESP301-driven UV-Vis film degradation example
- Update: driver import handling, initialization metadata, repeated-measure QC logging, and AM1.5 reference handling
- Not in scope: automated analysis filtering based on QC validity inside the decay calculation itself

#### Required Actions

- [x] Device class implemented
- [x] Initialization path checked
- [x] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [x] Example executed successfully
- [x] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result: local initialization succeeded with spectrometer key `UV-Vis`; manual dark/blank/sample absorbance example executed locally; spectral decay recalculation was validated against legacy `specdecay_sample` data with very high trend agreement
- Web app result:
- Known issues: vendor driver must be installed in the active Python environment

#### Notes

- `adjust_default_integration_time()` is used at the blank position and keeps the default target near `52000` counts
- Negative absorbance is clamped to `0` and high absorbance is capped at `5`, matching the older UV-Vis workflow
- Repeated absorbance measurements now append even when QC differences exceed threshold; validity and comparison statistics are logged separately in `sample_name_measurement_qc_log.csv`
- Spectral decay now follows the `UVVis_Converter` method more closely:
  - default spectral range `290-800 nm`
  - default irradiance reference `data/spectroscopy/reference/am15g_spectrum.csv`
  - spectral overlap computed by interpolating AM1.5 irradiance onto the measured wavelength grid and integrating with `trapz`
- Added `example_uvvis_film_absorbance_degradation.py` for ESP301 axis-3 sample rotation with:
  - dark measured once at startup
  - blank measured before every sample
  - loop count and active slots configured at the top of the example

#### Device: `Sonicator`

- Status: `done`
- Device file: `aamp_app/devices/sonicator.py`
- Command file: `aamp_app/commands/sonicator_commands.py`
- Example file: `examples/example_sonicator.py`
- Similar existing implementation: `to_implement/sonicator/test6/test6.ino`
- Hardware or SDK dependency: `Arduino Uno R3 wrapper for sonicator front-panel button/status wiring`

#### Scope

- Add: Sonicator device, commands, example, and cleaned-up Uno firmware sketch
- Update: web-app metadata and documentation stubs
- Not in scope: redesigning the sonicator hardware interface board

#### Required Actions

- [x] Device class implemented
- [x] Initialization path checked
- [x] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [x] Example executed successfully
- [ ] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result: Python smoke test executed locally on `COM13`
- Web app result:
- Known issues: `power` probing is intentionally treated as intrusive because it may toggle the front-panel button when the sonicator is idle

#### Notes

- Host-side protocol follows the final draft family in `to_implement/sonicator/test6/test6.ino`
- Command set: `>status`, `>button`, `>power`, `>turnon`, `>turnoff`
- Expected Uno R3 wiring is `5V`, `GND`, `D7` button drive, and `D8` status sense
- Added a cleaned-up firmware sketch at `firmware/sonicator/sonicator_uno_r3/sonicator_uno_r3.ino`

#### Device: `SubstrateHotel`

- Status: `in progress`
- Device file: `aamp_app/devices/substrate_hotel.py`
- Command file: `aamp_app/commands/substrate_hotel_commands.py`
- Example file: `examples/example_substrate_hotel.py`
- Similar existing implementation: `to_implement/substratehotel/substrate_hotel.py`
- Hardware or SDK dependency: `Arduino-based linear stage controller`

#### Scope

- Add: dedicated device, commands, example, and web-app metadata
- Update: current repo to use `Connect -> Initialize -> Move/Home -> Deinitialize` style
- Not in scope: Arduino firmware changes

#### Required Actions

- [x] Device class implemented
- [ ] Initialization path checked
- [ ] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [ ] Example executed successfully
- [ ] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result:
- Web app result:
- Known issues: current repo path not hardware-smoke-tested yet

#### Notes

- Serial protocol inferred from old draft: Arduino emits `Ready`, homing uses `H`, and absolute motion uses `M{position},{speed}`
- Current Python-side position guard is `0-430 mm`
- Default homing and move timeouts are `300 s`

#### Device: `SubstrateDispenser`

- Status: `in progress`
- Device file: `aamp_app/devices/substrate_dispenser.py`
- Command file: `aamp_app/commands/substrate_dispenser_commands.py`
- Example file: `examples/example_substrate_dispenser.py`
- Similar existing implementation: `to_implement/substratehotel/substrate_dispenser.py`
- Hardware or SDK dependency: `Arduino-based linear stage controller`

#### Scope

- Add: dedicated device, commands, example, and web-app metadata
- Update: current repo to use `Connect -> Initialize -> Move/Home -> Deinitialize` style
- Not in scope: Arduino firmware changes

#### Required Actions

- [x] Device class implemented
- [ ] Initialization path checked
- [ ] Shutdown or cleanup path checked
- [x] Core commands implemented
- [x] Command metadata and params reviewed
- [x] Example added or updated
- [ ] Example executed successfully
- [ ] Logging behavior checked
- [ ] Recipe or YAML compatibility checked
- [ ] Web app visibility checked
- [ ] Manual control page checked if applicable
- [ ] Execute recipe flow checked if applicable
- [x] Notes recorded

#### Validation

- Example run result:
- Web app result:
- Known issues: current repo path not hardware-smoke-tested yet

#### Notes

- Serial protocol inferred from old draft: Arduino emits `Ready`, homing uses `H`, and absolute motion uses `M{position},{speed}`
- Current Python-side position guard is `0-45 mm`
- Default homing and move timeouts are `30 s`

## Questions or Blockers

- None yet
