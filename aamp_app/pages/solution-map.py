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
    html.H1("Solution Map"),
    dbc.Alert(id="solution-map-alert", is_open=False, color="danger", className="mb-3"),
    dcc.Textarea(
        id="solution-map-json",
        style={"width": "100%", "height": "400px", "fontFamily": "monospace"},
        spellCheck=False,
    ),
    dbc.Button("Save", id="solution-map-save", color="primary", className="mt-2"),
], className="container")
