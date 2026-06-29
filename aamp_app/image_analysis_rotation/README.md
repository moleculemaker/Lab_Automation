# Pg2T-TT Webapp Rotation Bundle

This folder is a compact handoff package for applying the current Pg2T-TT derotation and rotation-based analysis outputs in another web app.

It intentionally uses the current post-Lightroom Pg2T-TT analysis stack only. Legacy folders, pre-Lightroom outputs, and exploratory scripts are excluded.

## What To Use In The Web App

The simplest integration target is:

- `sample_data/R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul/derived/webapp_payload.json`
- `sample_data/R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul/derived/angle_curve_long.csv`
- `sample_images/analysis_sample/`
- `sample_images/derotation_sample/`

The payload contains the derotation preset values, ROI preset, quality flags, compact fit summaries, and relative file links to the example figures.

The long CSV contains angle curves in this form:

```text
sample_id,source,mode,channel,angle_deg,value
```

where `source` is `sample_corr` or `blank_corr`, `mode` is `PPL` or `XPL`, and `channel` is `R`, `G`, or `B`.

`sample_images/analysis_sample/` contains sample-level QC/fit images and the full `0..165 deg` angle image series for the selected sample.

`sample_images/derotation_sample/` contains before/after derotation PNGs generated from all `rotation_calibration_3` angles, plus a contact sheet.

## Runtime Preset Values

Use these files when reproducing derotation behavior:

- `config/derotation_preset/solved_correction.json`
  - production solved rotation center
  - per-angle post-derotation translation table
- `config/derotation_preset/rotation_geometry.json`
  - safe all-angle geometry
  - valid mask bbox and safe rectangles
- `config/derotation_preset/rotation_valid_mask.png`
  - all-angle valid mask
- `config/roi_550_center.json`
  - current 550 px center ROI preset
- `config/derotation_preset/preset_values_summary.json`
  - compact human-readable summary of the above values

Current core values:

- derotation center, full resolution: `(x=1001.8200406419994, y=553.677412563412)`
- sample angles: `0..165 deg`, step `5 deg`
- derotation convention: rotate image counterclockwise by `angle_deg` around the solved center, then apply the per-angle translation from `solved_correction.json`
- ROI full resolution: `x=727`, `y=279`, `width=550`, `height=550`
- analysis ROI half resolution: `x=364`, `y=140`, `width=275`, `height=275`
- tile size/stride at half resolution: `64 / 32 px`

## Derotation QC Images

The derotation images are included because the numeric preset alone is not enough to verify sign conventions and safe-mask behavior.

- `derotation_qc_examples/rotation_geometry_overlay.png`
  - solved center and safe geometry overlay
- `derotation_qc_examples/rotation_corrected_preview.png`
  - selected corrected frames after derotation
- `derotation_qc_examples/overlay_all_angles.png`
  - all-angle overlay check
- `derotation_qc_examples/derotated_unmasked_contact_sheet.png`
  - contact sheet of derotated calibration frames before display masking

Additional all-angle before/after sample images:

- `sample_images/derotation_sample/rotation_calibration_3_<angle>_before.png`
- `sample_images/derotation_sample/rotation_calibration_3_<angle>_after.png`
- `sample_images/derotation_sample/rotation_calibration_3_before_after_contact_sheet.png`

The included angles are `000, 005, 010, ..., 165`.

## Example Sample

Primary example:

- `R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul`

Selection reason:

- not in the current final-results exclusion set
- strong `Afilm_PPL` A2 signal
- low Afilm fit NRMSE
- useful visual example for a webapp plot

Files:

- `derived/qc_metrics.json`
- `derived/roi_summary.csv`
- `derived/tile_fits.csv`
- `derived/sample_summary.json`
- `derived/extraction_metadata.json`
- `derived/extraction_bundle.npz`
- `figures/qc_curves.png`
- `figures/fit_overlay.png`
- `figures/representative_summary_blank_corrected.png`
- `sample_images/analysis_sample/all_angles/ppl/original/`
- `sample_images/analysis_sample/all_angles/ppl/derotated/`
- `sample_images/analysis_sample/all_angles/xpl/original/`
- `sample_images/analysis_sample/all_angles/xpl/derotated/`

## Regenerate The Webapp Payload

Run from this bundle folder or repository root:

```powershell
python .\pg2T-TT\distribution\pg2tt_webapp_rotation_bundle\scripts\export_webapp_payload.py
```

This writes:

- `sample_data/<sample_id>/derived/angle_curve_long.csv`
- `sample_data/<sample_id>/derived/webapp_payload.json`

## Scripts In This Folder

- `scripts/rotation_adapter.py`
  - standalone derotation helper that reads `config/derotation_preset/`
  - usable as importable Python functions or as a one-image CLI
- `scripts/export_webapp_payload.py`
  - rebuilds the webapp payload JSON and long angle table from the included derived outputs
- `scripts/fit_rotation_curves.py`
  - fits `a0 + a2c*cos(2theta) + a2s*sin(2theta) + a4c*cos(4theta) + a4s*sin(4theta)` from `angle_curve_long.csv`
  - writes `angle_curve_fit_summary.csv`
- `scripts/generate_analysis_sample_images.py`
  - regenerates the selected sample's all-angle PPL/XPL original and derotated PNG previews when the original source RAW folder is available
- `scripts/generate_derotation_sample_images.py`
  - regenerates the included all-angle before/after derotation sample PNGs when the original source RAW folder is available

Install requirements:

```powershell
pip install -r .\pg2T-TT\distribution\pg2tt_webapp_rotation_bundle\requirements.txt
```

Run the rotation fit example:

```powershell
python .\pg2T-TT\distribution\pg2tt_webapp_rotation_bundle\scripts\fit_rotation_curves.py
```

## Raw Data

The default bundle does not duplicate full RAW TIFF inputs. One representative sample alone is about 216 MB before adding blank, empty, and dark references.

Use `source_paths/raw_file_manifest.csv` to locate the source RAW folders in this repository if full raw-pipeline reproduction is needed.
