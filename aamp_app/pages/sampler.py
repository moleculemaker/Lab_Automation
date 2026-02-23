from dash import Dash, html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash

dash.register_page(__name__, path="/sampler", name="Sampler", title="Sampler")

SOLV_NAMES = ["CF", "CB", "CB9:A1", "CB8:A2", "CB7:A3", "1,4-Dichlorobenzene", "1,2,4-Trihlorobenzene", "o-xylene", "m-xylene", "p-xylene", "mesitylene", "toluene", "1-Chloronaphthalene", "anisole", "Tetrahydrofuran", "decane"]
CONCEN_D = [2, 5, 10, 15, 20]
PRINT_GAP_D = [50, 100]
PREC_VOL_D = [6, 9, 12]
MOTOR_SPEEDS_D = [0.01, 0.0355, 0.126, 0.4472, 1.587, 5.635, 20]
SPEED_C = (0.01, 20.0)
PREC_VOL_C = (6.0, 12.0)
CONCEN_C = (1, 5)

TEMP_CHOICES_D = {
    "CF": [25, 41.3], 
    "CB": [25, 47.3, 62.9, 87.6, 107.4], 
    "CB9:A1": [25, 47.3, 62.9, 87.6, 107.4],
    "CB8:A2": [25, 47.3, 62.9, 87.6, 107.4], 
    "CB7:A3": [25, 47.3, 62.9, 87.6, 107.4],
    "1,4-Dichlorobenzene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "1,2,4-Trihlorobenzene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "o-xylene": [25, 47.3, 62.9, 87.6, 107.4, 119.6],
    "m-xylene": [25, 47.3, 62.9, 87.6, 107.4, 114.6],
    "p-xylene": [25, 47.3, 62.9, 87.6, 107.4, 113.8],
    "mesitylene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "toluene": [25, 47.3, 55.1, 62.9, 75.1, 87.7],
    "1-Chloronaphthalene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "anisole": [25, 47.3, 62.9, 87.6, 107.4, 129.1],
    "Tetrahydrofuran": [25, 30.1, 35.4, 40, 45.7],
    "decane": [25, 47.3, 62.9, 87.6, 107.4, 135],
}

TEMP_CHOICES_C = {
    "CF": (25, 41.3),
    "CB": (25, 107.4),
    "CB9:A1": (25, 107.4),
    "CB8:A2": (25, 107.4),
    "CB7:A3": (25, 107.4),
    "1,4-Dichlorobenzene": (25, 135),
    "1,2,4-Trihlorobenzene": (25, 135),
    "o-xylene": (25, 119.6),
    "m-xylene": (25, 114.6),
    "p-xylene": (25, 113.8),
    "mesitylene": (25, 135),
    "toluene": (25, 87.7),
    "1-Chloronaphthalene": (25, 135),
    "anisole": (25, 129.1),
    "Tetrahydrofuran": (25, 45.7),
    "decane": (25, 135),
}

layout = html.Div(
    [
        html.Datalist(
            id="smiles-suggestions",
            children=[
                html.Option(value="{O=C(OCC(CCCC)[*]CCCCC)C1=C(C2=CC=CS2)SC(C(S3)=CC(C(OCC(CCCCCC)CCCC)=O)=C3C4=CC=[*]S4)=C1}"),
                html.Option(value="{COCCOCCOCCOC1=C(C2=C(OCCOCCOCCOC)C=C(S2)[*])SC(C3=CC4=C(S3)C=C(S4)[*])=C1}")
            ]
        ),
        html.Datalist(
            id="polymer-suggestions",
            children=[
                html.Option(value="PDCBT"),
                html.Option(value="P(g42T-TT)")
            ]
        ),
        html.Datalist(
            id="mw-suggestions",
            children=[
                html.Option(value="60000"),
                html.Option(value="40000")
            ]
        ),
        html.Datalist(
            id="pdi-suggestions",
            children=[
                html.Option(value="2.5")
            ]
        ),
        html.Div([
            html.H1([
                "Sampler",
                html.Span(
                    " ?",
                    id="sampler-help",
                    style={
                        "cursor": "pointer",
                        "color": "gray",
                        "fontWeight": "bold",
                        "fontSize": "0.7em",
                        "marginLeft": "10px"
                    }
                ),
            ], style={"display": "inline-block"}),
            dbc.Tooltip(
                "This page allows the user to generate starting parameter sets for a campaign, covering as much as the parameter space as possible so the optimizer can narrow down on particular runs that where successful. You can enter campaign-specific information, and discrete or continuous parameter values for the sampler to explore, and it will generate PCA and uMAP visualizations, the generated parameter values, and their min-max normalized value for the optimizer. This data can then be saved to the database and used in other pages of the app, namely the recipe builder, to start a campaign.",
                target="sampler-help",
                placement="right",
                style={"maxWidth": "350px"}
            ),
        ]),
        dbc.Alert(
            id="sampler-alert",
            color="success",
            is_open=False,
            fade=True,
            className="mb-3",
        ),
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H5("Campaign Name"),
                                dbc.Input(id="sampler-campaign-name", type="text", placeholder="Enter campaign name"),
                            ],
                            width=2,
                        ),
                        dbc.Col(
                            [
                                html.H5("Polymer Name"),
                                dbc.Input(id="sampler-polymer-name", type="text", placeholder="Enter polymer name", list="polymer-suggestions"),
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                html.H5("SMILES String"),
                                dbc.Input(id="sampler-smiles-string", type="text", placeholder="Enter SMILES string", list="smiles-suggestions"),
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                html.H5("Number-Averaged Molecular Weight (Mn)"),
                                dbc.Input(id="sampler-mw", type="number", placeholder="Enter Mn", min=0, list="mw-suggestions"),
                            ],
                            width=2,
                        ),
                        dbc.Col(
                            [
                                html.H5("Polydispersity Index (PDI)"),
                                dbc.Input(id="sampler-pdi", type="number", placeholder="Enter PDI", min=1, step=0.01, list="pdi-suggestions"),
                            ],
                            width=2,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H5("Upload Polymer Image"),
                                dcc.Upload(
                                    id="sampler-polymer-image",
                                    children=html.Div([
                                        'Drag and Drop or ',
                                        html.A('Select an Image')
                                    ]),
                                    style={
                                        'width': '100%',
                                        'height': '60px',
                                        'lineHeight': '60px',
                                        'borderWidth': '1px',
                                        'borderStyle': 'dashed',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'margin': '10px 0'
                                    },
                                    multiple=False,
                                    accept='image/*'
                                ),
                                html.Div(id="sampler-polymer-image-preview"),
                            ],
                            width=12,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H5("Upload GPC Data"),
                                dcc.Upload(
                                    id="gpc-data-upload",
                                    children=html.Div([
                                        'Drag and Drop or ',
                                        html.A('Select a CSV or Excel File')
                                    ]),
                                    style={
                                        'width': '100%',
                                        'height': '60px',
                                        'lineHeight': '60px',
                                        'borderWidth': '1px',
                                        'borderStyle': 'dashed',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'margin': '10px 0'
                                    },
                                    multiple=False,
                                    accept='.csv, .xlsx, .xls'
                                ),
                                html.Div(id="gpc-data-output")
                            ],
                            width=12,
                        ),
                    ],
                    className="mb-3",
                ),
                dcc.Store(id="gpc-data-store", storage_type="memory"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H5("Solvent"),
                                dcc.Dropdown(
                                    id="sampler-solvent-dropdown",
                                    options=[{"label": solv, "value": solv} for solv in SOLV_NAMES],
                                    multi=True,
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.H5("Temperature"),
                                    html.Div(id="sampler-temperature-options", children=[]),
                                ],
                                id="temperature-container",
                                style={'display': 'none'}
                            ),
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col([html.H5("Concentration Range")], width=2),
                        dbc.Col(
                            [
                                dbc.Switch(
                                    id={"type": "toggle", "param": "concentration"},
                                    label="Continuous",
                                    value=False,
                                ),
                            ],
                            width=2,
                        ),
                    ],
                    className="mb-2",
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dcc.Dropdown(
                                            id={"type": "sampler-dropdown", "id": "concentration"},
                                            options=[{"label": str(concen), "value": concen} for concen in CONCEN_D],
                                            multi=True,
                                            value=CONCEN_D,
                                        ),
                                    ],
                                    width=4,
                                ),
                                dbc.Col(
                                    dbc.InputGroup([
                                        dbc.Input(id={"type": "custom-input", "id": "concentration"}, type="number", placeholder="Custom concentration"),
                                        dbc.Button("Add", id={"type": "add-custom-button", "id": "concentration"}, size="sm"),
                                    ]),
                                    width=4,
                                )
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "discrete-container", "param": "concentration"},
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.InputGroup(
                                            [
                                                dbc.Input(id="concentration-min", type="number", placeholder="Min", value=CONCEN_C[0]),
                                                dbc.Input(id="concentration-max", type="number", placeholder="Max", value=CONCEN_C[1]),
                                            ]
                                        ),
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "continuous-container", "param": "concentration"},
                    style={"display": "none"},
                ),
                dbc.Row(
                    [
                        dbc.Col([html.H5("Printing Gap")], width=2),
                        dbc.Col(
                            [
                                dbc.Switch(
                                    id={"type": "toggle", "param": "printing-gap"},
                                    label="Continuous",
                                    value=False,
                                ),
                            ],
                            width=2,
                        ),
                    ],
                    className="mb-2",
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dcc.Dropdown(
                                            id={"type": "sampler-dropdown", "id": "printing-gap"},
                                            options=[{"label": str(gap), "value": gap} for gap in PRINT_GAP_D],
                                            multi=True,
                                            value=PRINT_GAP_D,
                                        ),
                                    ],
                                    width=4,
                                ),
                                dbc.Col(
                                    dbc.InputGroup([
                                        dbc.Input(id={"type": "custom-input", "id": "printing-gap"}, type="number", placeholder="Custom printing gap"),
                                        dbc.Button("Add", id={"type": "add-custom-button", "id": "printing-gap"}, size="sm"),
                                    ]),
                                    width=4,
                                )
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "discrete-container", "param": "printing-gap"},
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.InputGroup(
                                            [
                                                dbc.Input(id="printing-gap-min", type="number", placeholder="Min", value=PRINT_GAP_D[0]),
                                                dbc.Input(id="printing-gap-max", type="number", placeholder="Max", value=PRINT_GAP_D[-1]),
                                            ]
                                        ),
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "continuous-container", "param": "printing-gap"},
                    style={"display": "none"},
                ),
                dbc.Row(
                    [
                        dbc.Col([html.H5("Precursor Volume")], width=2),
                        dbc.Col(
                            [
                                dbc.Switch(
                                    id={"type": "toggle", "param": "precursor-volume"},
                                    label="Continuous",
                                    value=False,
                                ),
                            ],
                            width=2,
                        ),
                    ],
                    className="mb-2",
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dcc.Dropdown(
                                            id={"type": "sampler-dropdown", "id": "precursor-volume"},
                                            options=[{"label": str(vol), "value": vol} for vol in PREC_VOL_D],
                                            multi=True,
                                            value=PREC_VOL_D,
                                        ),
                                    ],
                                    width=4,
                                ),
                                dbc.Col(
                                    dbc.InputGroup([
                                        dbc.Input(id={"type": "custom-input", "id": "precursor-volume"}, type="number", placeholder="Custom precursor volume"),
                                        dbc.Button("Add", id={"type": "add-custom-button", "id": "precursor-volume"}, size="sm"),
                                    ]),
                                    width=4,
                                )
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "discrete-container", "param": "precursor-volume"},
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.InputGroup(
                                            [
                                                dbc.Input(id="precursor-volume-min", type="number", placeholder="Min", value=PREC_VOL_C[0]),
                                                dbc.Input(id="precursor-volume-max", type="number", placeholder="Max", value=PREC_VOL_C[1]),
                                            ]
                                        ),
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "continuous-container", "param": "precursor-volume"},
                    style={"display": "none"},
                ),
                dbc.Row(
                    [
                        dbc.Col([html.H5("Motor Speed Range")], width=2),
                        dbc.Col(
                            [
                                dbc.Switch(
                                    id={"type": "toggle", "param": "motor-speed"},
                                    label="Continuous",
                                    value=False,
                                ),
                            ],
                            width=2,
                        ),
                    ],
                    className="mb-2",
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dcc.Dropdown(
                                            id={"type": "sampler-dropdown", "id": "motor-speed"},
                                            options=[{"label": str(speed), "value": speed} for speed in MOTOR_SPEEDS_D],
                                            multi=True,
                                            value=MOTOR_SPEEDS_D,
                                        ),
                                    ],
                                    width=4,
                                ),
                                dbc.Col(
                                    dbc.InputGroup([
                                        dbc.Input(id={"type": "custom-input", "id": "motor-speed"}, type="number", placeholder="Custom motor speed"),
                                        dbc.Button("Add", id={"type": "add-custom-button", "id": "motor-speed"}, size="sm"),
                                    ]),
                                    width=4,
                                )
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "discrete-container", "param": "motor-speed"},
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.InputGroup(
                                            [
                                                dbc.Input(id="motor-speed-min", type="number", placeholder="Min", value=SPEED_C[0]),
                                                dbc.Input(id="motor-speed-max", type="number", placeholder="Max", value=SPEED_C[1]),
                                            ]
                                        ),
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "continuous-container", "param": "motor-speed"},
                    style={"display": "none"},
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H5("Sampling Method"),
                                dcc.Dropdown(
                                    id="sampler-method-dropdown",
                                    options=[
                                        {"label": "Sobol Sequence", "value": "sobol"},
                                        {"label": "Random Sampling", "value": "random"},
                                    ],
                                    value="sobol",
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                html.H5("Number of Samples per Solvent"),
                                dbc.Input(id="sampler-num-samples", type="number", value=5, min=1),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                
                dbc.Button(
                    "Generate Parameter Sets",
                    id="sampler-generate-button",
                    color="primary",
                    className="mb-3",
                ),
                
                html.Div(id="sampler-results-table", className="mb-3"),
                html.Div(id="sampler-results-plots", className="mb-3"),
                
                dbc.Button(
                    "Save Parameter Sets",
                    id="sampler-save-button",
                    color="success",
                    className="mb-3",
                    disabled=True,
                ),
            ],
            className="container",
        ),
    ],
    className="container",
)
