from pathlib import Path
from string import Template
import os
import sys

import dash
from dash import html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc

ROOT_DIR = Path(__file__).resolve().parents[2]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from mongodb_helper import MongoDBHelper
from console_interceptor import ConsoleInterceptor


TEMPLATE_PATH = ROOT_DIR / "recipes" / "user_recipes" / "ch_apis_imaging_from_mongodb.py"


def load_env(file_path: Path = ROOT_DIR / ".env") -> None:
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


def get_mongo() -> MongoDBHelper:
    load_env()
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_db_name = os.environ.get("MONGO_DB_NAME")
    if not mongo_uri or not mongo_db_name:
        raise RuntimeError("MONGO_URI and MONGO_DB_NAME must be set in .env.")
    return MongoDBHelper(mongo_uri, mongo_db_name)


with open(TEMPLATE_PATH, "r", encoding="utf-8") as file:
    CH_APIS_RECIPE_TEMPLATE = Template(file.read())


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1(
                    [
                        "CH APIS Imaging Builder Draft",
                        html.Span(
                            " ?",
                            id="ch-apis-builder-help",
                            style={
                                "cursor": "pointer",
                                "color": "gray",
                                "fontWeight": "bold",
                                "fontSize": "0.7em",
                                "marginLeft": "10px",
                            },
                        ),
                    ],
                    style={"display": "inline-block"},
                ),
                dbc.Tooltip(
                    "Standalone draft for APIS imaging recipe generation. "
                    "Select a campaign and it will list all sets that do not yet have APIS imaging records in the images collection. "
                    "Generated recipes perform MongoDB lookup at execution time using campaign_name, batch_no, and sample_no.",
                    target="ch-apis-builder-help",
                    placement="right",
                    style={"maxWidth": "420px"},
                ),
            ]
        ),
        dbc.Alert(
            id="ch-apis-alert",
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
                                html.H5("Select Campaign"),
                                dcc.Dropdown(
                                    id="ch-apis-campaign-dropdown",
                                    options=[],
                                    placeholder="Select a campaign...",
                                ),
                            ],
                            width=8,
                        ),
                        dbc.Col(
                            [
                                dbc.Button(
                                    "Generate Pending APIS Recipes",
                                    id="ch-apis-generate-button",
                                    color="primary",
                                    className="mt-4",
                                ),
                            ],
                            width=2,
                        ),
                        dbc.Col(
                            [
                                dbc.Button(
                                    "Run 0 recipes",
                                    id="ch-apis-run-button",
                                    n_clicks=0,
                                    className="btn btn-success mt-4",
                                ),
                            ],
                            width=2,
                        ),
                    ],
                    className="mb-3",
                ),
                html.Div(
                    [
                        html.H4("Pending Parameter Sets"),
                        html.Div(id="ch-apis-sets"),
                    ],
                    className="mb-3",
                ),
                html.Div(id="ch-apis-output", className="mb-3"),
                html.Div(id="ch-apis-run-log", className="mb-3"),
                dcc.Store(id="ch-apis-parameter-sets"),
                dcc.Store(id="ch-apis-generated-scripts"),
            ],
            className="container",
        ),
    ],
    className="container",
)


@callback(
    Output("ch-apis-campaign-dropdown", "options"),
    Input("ch-apis-campaign-dropdown", "search_value"),
)
def update_campaign_options(search_value):
    mongo = get_mongo()
    try:
        campaigns = list(mongo.db.campaigns.find({}, {"campaign_name": 1}))
        options = [{"label": doc["campaign_name"], "value": doc["campaign_name"]} for doc in campaigns]
        if search_value:
            options = [opt for opt in options if search_value.lower() in opt["label"].lower()]
        return options
    finally:
        mongo.close_connection()


@callback(
    Output("ch-apis-sets", "children"),
    Output("ch-apis-parameter-sets", "data"),
    Output("ch-apis-alert", "children"),
    Output("ch-apis-alert", "is_open"),
    Output("ch-apis-alert", "color"),
    Input("ch-apis-campaign-dropdown", "value"),
)
def display_pending_campaign_sets(selected_campaign):
    if not selected_campaign:
        return html.Div("Select a campaign to view pending APIS imaging sets."), [], "", False, "success"

    mongo = get_mongo()
    try:
        campaign = mongo.db.campaigns.find_one({"campaign_name": selected_campaign})
        if not campaign:
            return html.Div(f"Campaign '{selected_campaign}' was not found."), [], "Campaign not found.", True, "danger"

        sets = list(
            mongo.db.sets.find({"campaign_id": campaign["_id"]}).sort(
                [("batch_no", 1), ("sample_no", 1)]
            )
        )
        if not sets:
            return html.Div(f"No parameter sets found for campaign '{selected_campaign}'."), [], "No parameter sets found.", True, "warning"

        executed_set_ids = set(
            mongo.db.images.distinct(
                "set_id",
                {
                    "measurement_type": "apis_imaging",
                    "campaign_id": campaign["_id"],
                },
            )
        )
        pending_sets = [doc for doc in sets if doc["_id"] not in executed_set_ids]

        if not pending_sets:
            return (
                html.Div(f"All parameter sets for campaign '{selected_campaign}' already have APIS imaging records."),
                [],
                "No pending APIS imaging sets remain for this campaign.",
                True,
                "info",
            )

        table_rows = []
        for doc in pending_sets:
            table_rows.append(
                {
                    "set_id": str(doc["_id"]),
                    "batch_no": doc.get("batch_no"),
                    "sample_no": doc.get("sample_no"),
                    "polymer_name": doc.get("polymer_name"),
                    "solvent": doc.get("solvent"),
                    "concentration": doc.get("concentration"),
                    "motor_speed": doc.get("motor_speed"),
                    "temperature": doc.get("temperature"),
                    "printing_gap": doc.get("printing_gap"),
                    "precursor_volume": doc.get("precursor_volume"),
                }
            )

        table = dash_table.DataTable(
            id="ch-apis-sets-table",
            data=table_rows,
            columns=[
                {"name": "Batch No", "id": "batch_no"},
                {"name": "Sample No", "id": "sample_no"},
                {"name": "Polymer", "id": "polymer_name"},
                {"name": "Solvent", "id": "solvent"},
                {"name": "Conc.", "id": "concentration"},
                {"name": "Speed", "id": "motor_speed"},
                {"name": "Temp", "id": "temperature"},
                {"name": "Gap", "id": "printing_gap"},
                {"name": "Volume", "id": "precursor_volume"},
            ],
            selected_rows=list(range(len(table_rows))),
            row_selectable="multi",
            page_size=12,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left"},
        )
        msg = f"Loaded {len(table_rows)} pending APIS imaging sets for campaign '{selected_campaign}'."
        return table, table_rows, msg, True, "success"
    finally:
        mongo.close_connection()


@callback(
    Output("ch-apis-run-button", "children"),
    Input("ch-apis-parameter-sets", "data"),
    Input("ch-apis-sets-table", "selected_rows"),
    prevent_initial_call=False,
)
def update_run_button_label(parameter_sets, selected_rows):
    if not parameter_sets:
        return "Run 0 recipes"
    num_recipes = len(selected_rows) if selected_rows else 0
    return f"Run {num_recipes} recipe{'s' if num_recipes != 1 else ''}"


@callback(
    Output("ch-apis-output", "children"),
    Output("ch-apis-generated-scripts", "data"),
    Input("ch-apis-generate-button", "n_clicks"),
    State("ch-apis-sets-table", "selected_rows"),
    State("ch-apis-parameter-sets", "data"),
    State("ch-apis-campaign-dropdown", "value"),
    prevent_initial_call=True,
)
def generate_pending_apis_recipes(n_clicks, selected_rows, parameter_sets, selected_campaign):
    if not selected_campaign:
        return html.Div("Select a campaign first.", style={"color": "red"}), []
    if not parameter_sets:
        return html.Div("No pending parameter sets are available.", style={"color": "red"}), []
    if not selected_rows:
        return html.Div("Select at least one parameter set.", style={"color": "red"}), []

    generated_scripts = []
    for idx in selected_rows:
        params = parameter_sets[idx]
        sub_dict = {
            "campaign_name": selected_campaign,
            "batch_no": params["batch_no"],
            "sample_no": params["sample_no"],
        }
        script = CH_APIS_RECIPE_TEMPLATE.safe_substitute(sub_dict)
        generated_scripts.append(
            {
                "batch_no": params["batch_no"],
                "sample_no": params["sample_no"],
                "script": script,
            }
        )

    return (
        html.Div(
            [
                html.H4("Generated APIS Imaging Recipes"),
                html.Ul(
                    [
                        html.Li(
                            [
                                html.P(f"Batch {entry['batch_no']} Sample {entry['sample_no']}"),
                                html.Pre(
                                    entry["script"],
                                    style={
                                        "height": "420px",
                                        "overflowY": "auto",
                                        "backgroundColor": "#f8f9fa",
                                        "padding": "10px",
                                        "border": "1px solid #dee2e6",
                                    },
                                ),
                            ]
                        )
                        for entry in generated_scripts
                    ]
                ),
            ]
        ),
        generated_scripts,
    )


@callback(
    Output("ch-apis-run-log", "children"),
    Input("ch-apis-run-button", "n_clicks"),
    State("ch-apis-generated-scripts", "data"),
    prevent_initial_call=True,
)
def run_generated_apis_recipes(n_clicks, generated_scripts):
    if not generated_scripts:
        return html.Div("No generated recipes to run.", style={"color": "red"})

    log_components = []
    interceptor = ConsoleInterceptor()

    try:
        for entry in generated_scripts:
            code = entry["script"]
            log_components.append(html.H5(f"Running Batch {entry['batch_no']} Sample {entry['sample_no']}"))

            interceptor.start_interception()
            try:
                exec(code)
                status = "Success"
                alert_color = "success"
            except Exception as exc:
                status = f"Error: {str(exc)}"
                alert_color = "danger"
            finally:
                interceptor.stop_interception()

            output = interceptor.get_intercepted_messages()
            log_components.extend(
                [
                    dbc.Alert(status, color=alert_color),
                    html.Pre(
                        f"Output:\n{''.join(output)}",
                        style={
                            "backgroundColor": "#f8f9fa",
                            "padding": "10px",
                            "border": "1px solid #dee2e6",
                            "maxHeight": "300px",
                            "overflowY": "auto",
                        },
                    ),
                    html.Hr(),
                ]
            )
            interceptor.intercepted_messages = []

        return log_components
    finally:
        del interceptor


if __name__ == "__main__":
    app.run(debug=True, port=8051)
