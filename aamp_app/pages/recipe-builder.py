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
                dash.dash_table.DataTable(
                    id='parameter-sets-table',
                    columns=[
                        {'name': 'Sample No', 'id': 'sample_no'},
                        {'name': 'Motor Speed', 'id': 'motor_speed'},
                        {'name': 'Temperature', 'id': 'temperature'},
                        {'name': 'Concentration', 'id': 'concentration'},
                        {'name': 'Printing Gap', 'id': 'printing_gap'},
                        {'name': 'Precursor Volume', 'id': 'precursor_volume'},
                        {'name': 'Solvent', 'id': 'solvent'}
                    ],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    row_selectable='multi',
                    selected_rows=[]
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