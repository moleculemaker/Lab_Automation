from dash import html, dcc
import dash
import dash_bootstrap_components as dbc

dash.register_page(
    __name__,
    path="/solution-map",
    name="Solution Map",
    title="Solution Map"
)

layout = html.Div([
    html.Div([
        html.H1([
            "Solution Map",
            html.Span(
                " ?",
                id="solution-map-help",
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
            "This page allows you to view and edit the solution map. Each nested object in the JSON represents a cell with a polymer, solvent, and concentration. You can update the map and save changes to the database. Use this to manage which solutions are available in each position (A1-D5). When the recipe builder generates recipe templates, it uses the information from each parameter set and this solution map to decide where to move the handler arm.",
            target="solution-map-help",
            placement="right",
            style={"maxWidth": "350px"}
        ),
    ]),
    dbc.Alert(id="solution-map-alert", is_open=False, color="danger", className="mb-3"),
    dcc.Textarea(
        id="solution-map-json",
        style={"width": "100%", "height": "400px", "fontFamily": "monospace"},
        spellCheck=False,
    ),
    dbc.Button("Save", id="solution-map-save", color="primary", className="mt-2"),
], className="container")
