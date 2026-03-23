# Device Ports

This file tracks the current local serial port assignments and related connection settings for lab hardware used in this repository.

## Notes

- Update this file when a device moves to a new port.
- If a port changes, update the related example, recipe, or web app configuration as needed.
- These values are machine-specific and may differ across lab PCs.

## Current Assignments

| Device Name | Model / Controller | Vendor | Port | Baudrate | Notes | Related Files |
| --- | --- | --- | --- | --- | --- | --- |
| `esp301_3n` | `ESP301-3N` with `axis1=ILS100CC`, `axis2=UTS100PP`, `axis3=PR50PP` | Newport | `COM6` | `921600` | Axis homing config: `OR4 / OR4 / OR1` | `examples/example_esp301_3n.py`, `recipes/recipe_sample.py`, `aamp_app/util.py` |
| `linear_stage_150` | `LTS150` / `LinearStage150` | Thorlabs | `COM15` | `115200` | Smoke test updated locally to use `COM15`; initial absolute move tested at `100 mm` | `examples/example_linear_stage_150.py`, `aamp_app/util.py` |
| `z812` | `Z812` with `KDC101` | Thorlabs | `COM12` | `115200` | Smoke test passed locally with absolute move `8 mm` and relative move `3 mm` | `examples/example_z812.py`, `aamp_app/util.py`, `aamp_app/devices/z812.py` |
| `newport_94043a_solar_sim` | `94043A` solar simulator via `69920` power supply | Newport | `COM11` | `9600` | RS-232 via USB adapter; default control path is power mode; initialize applies `400 W` preset and software blocks presets above `450 W`; lamp replacement warning starts at `1000 h` | `examples/example_94043a_solar_sim.py`, `aamp_app/util.py`, `aamp_app/devices/newport_94043a_solar_sim.py` |

## To Fill Later

| Device Name | Model / Controller | Vendor | Port | Baudrate | Notes | Related Files |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |
