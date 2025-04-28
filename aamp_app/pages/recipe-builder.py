from dash import Dash, html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import dash

dash.register_page(__name__, path="/recipe-builder", name="Recipe Builder", title="Recipe Builder")

layout = html.Div(
    [
        html.H1("Recipe Builder"),
        dbc.Alert(
            id="recipe-alert",
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
                                    id="recipe-builder-campaign-dropdown",
                                    options=[],
                                    placeholder="Select a campaign..."
                                ),
                            ],
                            width=12,
                        ),
                    ],
                    className="mb-3",
                ),
                html.Div(
                    [
                        html.H4("Parameter Sets for Selected Campaign"),
                        html.Div(id="recipe-builder-sets")
                    ],
                    className="mb-3"
                ),
                html.Div(id="recipe-output", className="mb-3"),
                dcc.Store(id='recipe-parameter-sets'),
                dbc.Button(
                    "Generate Selected Recipes",
                    id="recipe-generate-button",
                    color="primary",
                    className="mb-3",
                ),
            ],
            className="container",
        ),
    ],
    className="container",
)