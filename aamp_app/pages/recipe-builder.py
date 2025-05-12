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
                        width=8,
                    ),
                    dbc.Col(
                        [
                            html.H5("Enter Solution Position"),
                            dcc.Input(
                                id="recipe-builder-solution-position",
                                type="text",
                                placeholder="A1-D5"
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Generate Selected Recipes",
                                id="recipe-builder-generate-button",
                                color="primary",
                                className="mb-3",
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                "Run 0 recipes",
                                id="recipe-builder-run-button",
                                n_clicks=0,
                                className="btn btn-success mt-2"
                            ),
                        ],
                        width=2,
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
            html.Div(id="recipe-builder-output", className="mb-3"),
            dcc.Store(id='recipe-builder-polymer-name'),
            dcc.Store(id='recipe-builder-parameter-sets'),
            dcc.Store(id="recipe-builder-generated-scripts"),
        ],
        className="container",
    )
],
className="container",
)