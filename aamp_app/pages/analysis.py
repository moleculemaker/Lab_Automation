import json
from pathlib import Path
import base64
import pandas as pd
import plotly.express as px
import dash
from dash import html, dcc, Input, Output, callback

# =====================================================
# Paths
# =====================================================

BASE_DIR = Path("image_analysis_rotation")

PAYLOAD_PATH = (
    BASE_DIR
    / "sample_data"
    / "R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul"
    / "derived"
    / "webapp_payload.json"
)

CURVE_PATH = (
    BASE_DIR
    / "sample_data"
    / "R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul"
    / "derived"
    / "angle_curve_long.csv"
)

IMAGE_DIR = (
    BASE_DIR
    / "sample_images"
    / "analysis_sample"
)

# =====================================================
# Load data
# =====================================================

with open(PAYLOAD_PATH, "r") as f:
    payload = json.load(f)

curve_df = pd.read_csv(CURVE_PATH)

def get_image_files(image_dir):
    exts = {".png", ".jpg", ".jpeg"}
    return sorted(
        [
            p
            for p in image_dir.rglob("*")
            if p.suffix.lower() in exts
        ]
    )


def image_to_base64(path):
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    ext = path.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"

    return f"data:image/{ext};base64,{encoded}"

IMAGE_FILES = get_image_files(IMAGE_DIR)

IMAGE_OPTIONS = [
    {
        "label": str(img.relative_to(IMAGE_DIR)),
        "value": str(img),
    }
    for img in IMAGE_FILES
]

dash.register_page(
    __name__,
    path="/analysis",
    name="Analysis",
    title="Analysis"
)

layout = html.Div(
    [
        html.H1("Pg2T-TT Rotation Analysis"),

        html.Hr(),

        html.Div(
            [
                html.H3("Sample Information"),

                html.Pre(
                    json.dumps(payload, indent=2),
                    style={
                        "maxHeight": "400px",
                        "overflowY": "scroll",
                        "border": "1px solid lightgray",
                        "padding": "10px",
                    },
                ),
            ]
        ),

        html.Hr(),

        html.H3("Angle Curves"),

        html.Div(
            [
                html.Label("Source"),
                dcc.Dropdown(
                    id="source-dropdown",
                    options=[
                        {"label": x, "value": x}
                        for x in sorted(curve_df["source"].unique())
                    ],
                    value=curve_df["source"].unique()[0],
                    clearable=False,
                ),
            ],
            style={"width": "25%", "display": "inline-block"},
        ),

        html.Div(
            [
                html.Label("Mode"),
                dcc.Dropdown(
                    id="mode-dropdown",
                    options=[
                        {"label": x, "value": x}
                        for x in sorted(curve_df["mode"].unique())
                    ],
                    value=curve_df["mode"].unique()[0],
                    clearable=False,
                ),
            ],
            style={
                "width": "25%",
                "display": "inline-block",
                "marginLeft": "20px",
            },
        ),

        dcc.Graph(id="angle-curve-graph"),

        html.Hr(),

        html.H3("Image Viewer"),

        dcc.Dropdown(
            id="image-dropdown",
            options=IMAGE_OPTIONS,
            value=IMAGE_OPTIONS[0]["value"] if IMAGE_OPTIONS else None,
            clearable=False,
        ),

        html.Br(),

        html.Div(
            [
                html.Img(
                    id="selected-image",
                    style={
                        "maxWidth": "100%",
                        "maxHeight": "900px",
                        "border": "1px solid lightgray",
                    },
                )
            ]
        ),
    ],
    style={"padding": "20px"},
)


@callback(
    Output("angle-curve-graph", "figure"),
    Input("source-dropdown", "value"),
    Input("mode-dropdown", "value"),
)
def update_curve(source, mode):

    dff = curve_df[
        (curve_df["source"] == source)
        & (curve_df["mode"] == mode)
    ]

    fig = px.line(
        dff,
        x="angle_deg",
        y="value",
        color="channel",
        color_discrete_map={
        "R": "red",
        "G": "green",
        "B": "blue",
    },
        markers=True,
        title=f"{source} | {mode}",
    )

    fig.update_layout(
        xaxis_title="Angle (deg)",
        yaxis_title="Intensity",
    )

    return fig

@callback(
    Output("selected-image", "src"),
    Input("image-dropdown", "value"),
)
def update_image(image_path):

    if not image_path:
        return None

    return image_to_base64(Path(image_path))