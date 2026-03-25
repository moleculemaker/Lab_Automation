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
| `heater` | `HeatingStage` Arduino controller | Custom | `COM16` | `115200` | Smoke test updated locally; supports non-blocking setpoint command and explicit wait-for-temperature hold check | `examples/example_heating_stage.py`, `aamp_app/util.py`, `aamp_app/devices/heating_stage.py` |
| `linear_stage_150` | `LTS150` / `LinearStage150` | Thorlabs | `COM15` | `115200` | Smoke test updated locally to use `COM15`; initial absolute move tested at `100 mm` | `examples/example_linear_stage_150.py`, `aamp_app/util.py` |
| `z812` | `Z812` with `KDC101` | Thorlabs | `COM12` | `115200` | Smoke test passed locally with absolute move `8 mm` and relative move `3 mm` | `examples/example_z812.py`, `aamp_app/util.py`, `aamp_app/devices/z812.py` |
| `newport_94043a_solar_sim` | `94043A` solar simulator via `69920` power supply | Newport | `COM11` | `9600` | RS-232 via USB adapter; default control path is power mode; initialize applies `400 W` preset and software blocks presets above `450 W`; lamp replacement warning starts at `1000 h` | `examples/example_94043a_solar_sim.py`, `aamp_app/util.py`, `aamp_app/devices/newport_94043a_solar_sim.py` |
| `p4pp` | `P4PP` Arduino controller | PolyPrint Illinois | `COM19` | `115200` | Rotation is blocked when linear position is `>= 45.0 mm`; explicit measurement resistor selection supported with default `681 ohm`; measurement default cycles set to `20` | `examples/example_p4pp.py`, `aamp_app/util.py`, `aamp_app/devices/p4pp.py` |
| `apis` | `APIS` Arduino controller + Ximea camera | PolyPrint Illinois | `COM8` | `9600` | Composite device for stage control and imaging; default image root is `data/imaging/`; current example writes mode-organized outputs under `data/imaging/demo_campaign/` | `examples/example_apis.py`, `aamp_app/util.py`, `aamp_app/devices/apis.py` |

## To Fill Later

| Device Name | Model / Controller | Vendor | Port | Baudrate | Notes | Related Files |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Storage Notes

- `APIS` image outputs default to `data/imaging/`
- `P4PP` measurement CSV outputs default to `data/resistance/p4pp_measurements.csv`
