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
- [ ] Device 5: `TBD`

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

## Questions or Blockers

- None yet
