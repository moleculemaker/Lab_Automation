import torch
import pandas as pd
from pathlib import Path

from dash import html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash
import io
import contextlib
from Image_Processing.image_processing_changhyun import *
from Image_Processing.constrained_bo_ver2 import ConstrainedBayesianOptimizer

dash.register_page(
    __name__,
    path="/manual-run",
    name="Manual Run",
    title="Manual Run"
)

layout = html.Div([
        html.Div([
        html.H2("Manual Bayesian Optimization Run"),
        # Additional layout components can be added here
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.H5("Upload Training Data"),
                    dcc.Upload(
                        id='manual-upload-data',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select a CSV File')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        multiple=False,
                        accept='.csv'
                    ),
                    html.Div(id='manual-upload-data-output')
                ], width=12)
            ], className="mb-3"),
            dbc.Button("Run Optimization", id="manual-run-optimization-btn", color="primary"),
            html.Pre(id="manual-optimization-output", style={"whiteSpace": "pre-wrap", "border": "1px solid #ccc", "padding": "10px", "marginTop": "10px"})
        ])
    ]),
    html.Div(
        [
            html.H2("Image Processing"),
            dbc.Input(id="data-path-input", placeholder="Enter input data path...", type="text"),
            dbc.Button("Process Image", id="process-image-btn", color="primary", className="mt-2"),
            html.Table(id="manual-image-processing-output", style={"whiteSpace": "pre-wrap", "border": "1px solid #ccc", "padding": "10px", "marginTop": "10px"})
        ]
    )
])

@callback(
    Output('manual-optimization-output', 'children'),
    Input('manual-run-optimization-btn', 'n_clicks'),
    State('manual-upload-data', 'contents'),
    State('manual-upload-data', 'filename')
)
def run_manual_optimization(n_clicks, contents, filename):
    if n_clicks is None or contents is None:
        return "No data uploaded yet."
    
    f = io.StringIO()
    bounds = torch.tensor([
        [0.01, 20.0],      # Speed
        [25.0, 107.0],     # Temperature
        [50, 200],         # Gap
        [5, 15]            # Volume
    ]).T

    # Define discrete points for each parameter
    discrete_points = [
        torch.tensor([0.1, 0.5, 0.7, 1.0]),  # Speed (if discrete)
        torch.tensor(list(range(25, 108))),  # Temperature
        torch.tensor(list(range(50, 201))),  # Gap
        torch.tensor(list(range(5, 16)))    # Volume
    ]

    csv_path = 'Round0/PProDOT_CB_Campaign_parameters.csv'
    optimizer = ConstrainedBayesianOptimizer(
        bounds=bounds,
        csv_path=csv_path,
        round_num=0,
        batch_size=8,
        discrete_or_not=[False, True, True, True],
        discrete_points=discrete_points
    )

    # Suggest candidates
    with contextlib.redirect_stdout(f):
        candidates, metadata = optimizer.suggest()
    print("\n" + "=" * 60)
    print("CONSTRAINED BO CANDIDATES READY")
    print("=" * 60)
    log = f.getvalue()
    return log

@callback(
    Output('manual-image-processing-output', 'children'),
    Input('process-image-btn', 'n_clicks'),
    State('data-path-input', 'value')
)
def img_proc(n_clicks, data_path):
    if n_clicks is None:
        return "Image processing not started yet."
    
    main_dirs = [
        Path("Image_Processing/Round0"),
        # Path("data/Round0_1"),
        # Path("data/Round0_2"),
        # Path("data/Round0_3"),
        # Path("data/Round1"),
        # Path("data/Round2"),
        # Path("data/Round3"),
        # Path("data/Round4"),
        # Path("data/Round5"),
        # Path("data/PProDOT_2nd_dataset")
        # Add desired directories
    ]
    
    # Method 2: Automatically discover all Round* directories under data/ (comment out Method 1 first)
    # data_base = Path("data")
    # if data_base.exists():
    #     main_dirs = [d for d in data_base.iterdir() if d.is_dir() and d.name.startswith("Round")]
    # else:
    #     main_dirs = []
    
    # Common settings
    roi_x = 580
    roi_y = 400
    roi_width = 913
    roi_height = 415
    
    # Thresholds
    uvvis_abs_threshold = 0.1
    coverage_threshold = 0.1
    
    # Common metadata (reference_dir and uvvis_dir are automatically set for each directory)
    metadata_base = {
        "roi_x": roi_x,
        "roi_y": roi_y,
        "roi_width": roi_width,
        "roi_height": roi_height,
        "uvvis_abs_threshold": uvvis_abs_threshold,
        "coverage_threshold": coverage_threshold,
        "coverage_k": 1.0,
        "uniformity_std_sensitivity": 15.0,  # K1: Sensitivity to Std difference
        "uniformity_ent_sensitivity": 2.0,   # K2: Sensitivity to Entropy difference
    }
    
    # Process each directory
    for main_dir in main_dirs:
        if not main_dir.exists():
            print(f"Warning: Directory not found: {main_dir}, skipping...")
            continue
        
        results = None
        try:
            results = process_single_directory(
                main_dir=main_dir,
                roi_x=roi_x,
                roi_y=roi_y,
                roi_width=roi_width,
                roi_height=roi_height,
                uvvis_abs_threshold=uvvis_abs_threshold,
                coverage_threshold=coverage_threshold,
                metadata_base=metadata_base,
            )
        except Exception as e:
            print(f"Error processing {main_dir}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*60}")
    print("All directories processed!")
    print(f"{'='*60}")

    # Create DataFrame for display
    df_results = pd.DataFrame(results)
    # only need a few columns for display
    display_columns = ["round#", "Sample #", "image_name", "uniformity_score"]
    df_display = df_results[display_columns]
    return dash_table.DataTable(
        data=df_display.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df_display.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
    )