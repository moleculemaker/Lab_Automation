from dash import Dash, html, dcc, dash_table, Input, Output, callback
import dash_bootstrap_components as dbc
import dash

dash.register_page(__name__, "/")

# layout = html.Div(
#     [
#         html.H1("Home"),
#         dcc.Input(id="filename-input", type="text", placeholder="Enter filename name"),
#         dbc.Button("Load", id="filename-input-button", n_clicks=0),
#         html.Div(id="home-output"),
#         dbc.Button("Refresh List", id="home-refresh-list-button", n_clicks=0),
#         dash_table.DataTable(
#             id="home-recipes-list-table",
#             columns=[
#                 {"name": "File Name", "id": "file_name"},
#                 #   {'name':'Posix', 'id':'posix_friendly'}
#             ],
#             data=[],
#             style_table={"width": "300px"},
#             style_cell={"textAlign": "left"},
#         ),
#     ]
# )

links = {
    "Load Recipe": "/load-recipe",
    "View/Edit Recipe": "/view-recipe",
    "Edit Recipe Code": "/edit-recipe",
    "Recipe Document": "/data",
    "Execute Recipe": "/execute-recipe",
    "Manual Control": "/manual-control",
    "Database Browser": "/database-browser",
    "Real Time Telemetry": "/real-time-telemetry",
    # "Images": "/images",
    "Sampler": "/sampler",
    "Recipe Builder": "/recipe-builder",
    "Solution Map": "/solution-map",
    "Autonomous Run": "/bayesian-optimization",
    "Manual Run": "/manual-run",
    "Analysis": "/analysis"
    # "Options": "/options",
}

layout = html.Div(
    [
        html.H1("Home", className="mb-3"),
        # dbc.Row(
        #     dbc.Col(
        #         dbc.Card(
        #             [
        #                 dbc.ListGroup(
        #                     [
        #                         dbc.ListGroupItem(
        #                             dbc.NavLink(
        #                                 link_name, href=link_path, external_link=True
        #                             )
        #                         )
        #                         for link_name, link_path in links.items()
        #                     ],
        #                     flush=True,
        #                 ),
        #             ]
        #         ),
        #         width=6,
        #         className="mx-auto mt-5",
        #     )
        # ),
        dbc.Row(
            [
                html.A(
                    dbc.Card(
                        dbc.CardBody(
                            dbc.NavLink(link_name, href=link_path, external_link=True)
                        ),
                        className="mb-3",
                    ),
                    href=link_path,
                    style={"width": "30%"},
                )
                for link_name, link_path in links.items()
            ],
            style={"justifyContent": "space-around"},
        )
        # dbc.Row(
        #     [
        #         dbc.Col(
        #             dcc.Input(
        #                 id="filename-input",
        #                 type="text",
        #                 placeholder="Enter file name",
        #                 className="form-control",
        #             ),
        #             width=6,
        #         ),
        #         dbc.Col(
        #             dbc.Button(
        #                 "Load",
        #                 id="filename-input-button",
        #                 n_clicks=0,
        #                 color="primary",
        #                 className="btn btn-primary",
        #             ),
        #             width=2,
        #         ),
        #     ],
        #     className="mb-3",
        # ),
        # dbc.Alert(
        #     id="home-load-file-alert",
        #     color="success",
        #     is_open=False,
        #     # fade=True,
        #     className="mb-3",
        # ),
        # dbc.Row(
        #     [
        #         dbc.Col(
        #             dbc.Button(
        #                 "Refresh List",
        #                 id="home-refresh-list-button",
        #                 n_clicks=0,
        #                 color="secondary",
        #                 className="btn btn-secondary mb-3",
        #             ),
        #             width=2,
        #         )
        #     ]
        # ),
        # dbc.Row(
        #     [
        #         dbc.Col(
        #             dash_table.DataTable(
        #                 id="home-recipes-list-table",
        #                 columns=[
        #                     {"name": "File Name", "id": "file_name"},
        #                     {"name": "Posix Compatible", "id": "posix_friendly"},
        #                     {"name": "Viewer Compatible", "id": "dash_friendly"},
        #                     {"name": "Python Code Available", "id": "python_code"},
        #                 ],
        #                 data=[],
        #                 style_table={"width": "100%"},
        #                 style_cell={"textAlign": "left"},
        #                 style_header={"fontWeight": "bold"},
        #                 page_current=0,
        #                 page_size=10,
        #                 style_data_conditional=[
        #                     {
        #                         "if": {
        #                             "column_id": "posix_friendly",
        #                             "filter_query": "{posix_friendly} contains true",
        #                         },
        #                         "backgroundColor": "#b7e8c4",
        #                         "color": "black",
        #                     },
        #                     {
        #                         "if": {
        #                             "column_id": "posix_friendly",
        #                             "filter_query": "{posix_friendly} contains false",
        #                         },
        #                         "backgroundColor": "#e8b7b7",
        #                         "color": "black",
        #                     },
        #                     {
        #                         "if": {
        #                             "column_id": "dash_friendly",
        #                             "filter_query": "{dash_friendly} contains true",
        #                         },
        #                         "backgroundColor": "#b7e8c4",
        #                         "color": "black",
        #                     },
        #                     {
        #                         "if": {
        #                             "column_id": "dash_friendly",
        #                             "filter_query": "{dash_friendly} contains false",
        #                         },
        #                         "backgroundColor": "#e8b7b7",
        #                         "color": "black",
        #                     },
        #                     {
        #                         "if": {
        #                             "column_id": "python_code",
        #                             "filter_query": "{python_code} contains true",
        #                         },
        #                         "backgroundColor": "#b7e8c4",
        #                         "color": "black",
        #                     },
        #                     {
        #                         "if": {
        #                             "column_id": "python_code",
        #                             "filter_query": "{python_code} contains false",
        #                         },
        #                         "backgroundColor": "#e8b7b7",
        #                         "color": "black",
        #                     },
        #                 ],
        #             ),
        #             width=10,
        #         )
        #     ]
        # ),
    ],
    className="container",
)
