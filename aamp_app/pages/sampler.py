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
        html.H1("Sampler"),
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
                                dbc.Input(id="sampler-polymer-name", type="text", placeholder="Enter polymer name"),
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                html.H5("SMILE String"),
                                dbc.Input(id="sampler-smile-string", type="text", placeholder="Enter SMILE string"),
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                html.H5("Molecular Weight"),
                                dbc.Input(id="sampler-mw", type="number", placeholder="Enter MW", min=0),
                            ],
                            width=2,
                        ),
                        dbc.Col(
                            [
                                html.H5("Polydispersity Index"),
                                dbc.Input(id="sampler-pdi", type="number", placeholder="Enter PDI", min=1, step=0.01),
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
                html.H5("Concentration Range"),
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

                # Modify the printing gap section
                html.H5("Printing Gap"),
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

                # Modify the precursor volume section
                html.H5("Precursor Volume"),
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
                dbc.Col(
                    [
                        html.H5("Motor Speed Range"),
                        dbc.InputGroup(
                            [
                                dbc.Input(id="sampler-motor-speed-min", type="number", placeholder="Min", value=SPEED_C[0]),
                                dbc.Input(id="sampler-motor-speed-max", type="number", placeholder="Max", value=SPEED_C[1]),
                            ]
                        ),
                    ],
                    width=4,
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
                                        {"label": "Latin Hypercube Sampling", "value": "lhs"},
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
