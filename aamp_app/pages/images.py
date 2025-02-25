from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash

dash.register_page(__name__, path="/images", name="Images", title="Upload Images")

layout = html.Div(
    [
        html.H1("Upload Images to MongoDB"),
        dbc.Alert(
            id="images-alert",
            color="success",
            is_open=False,
            fade=True,
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Input(id="sample-number", type="number", placeholder="Sample Number"), width=4),
                dbc.Col(dbc.Input(id="motor-speed", type="number", placeholder="Motor Speed"), width=4),
                dbc.Col(dbc.Input(id="temperature", type="number", placeholder="Temperature"), width=4),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Input(id="concentration", type="number", placeholder="Concentration"), width=4),
                dbc.Col(dbc.Input(id="printing-gap", type="number", placeholder="Printing Gap"), width=4),
                dbc.Col(dbc.Input(id="precursor-volume", type="number", placeholder="Precursor Volume"), width=4),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Input(id="solvent", type="text", placeholder="Solvent"), width=6),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dcc.Upload(
                    id="image-upload",
                    children=html.Div(["Drag and Drop or ", html.A("Select an Image")]),
                    style={
                        "width": "100%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "margin": "10px",
                    },
                    multiple=False,
                ),
            ],
            className="mb-3",
        ),
        dbc.Button("Upload Image", id="upload-image-button", color="primary"),
        html.Div(id="upload-status", style={"marginTop": "20px"}),
    ],
    className="container",
)
