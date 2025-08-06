from dash import html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

dash.register_page(
    __name__,
    path="/bayesian-optimization",
    name="Optimization",
    title="Optimization"
)

layout = html.Div(
    [
        html.Div([
            html.H1([
                "Optimization",
                html.Span(
                    " ?",
                    id="recipe-builder-help",
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
                "This page uses parameter sets generated in the sampler to create recipe templates to run on the devices. Selecting a campaign brings up all the parameter sets associated with it, and uses the solution map to determine each set's corresponding solution position. Generating recipes uses string template matching to fill in the templates with the set information and lets the user preview the results. You can also run all of the recipes sequentially.",
                target="recipe-builder-help",
                placement="right",
                style={"maxWidth": "350px"}
            ),
        ]),
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
                ],
                className="mb-3",
            ),
        ],
        className="container",
    ),
    # html.Div([
    #     html.H4("Campaign Progress"),
    #     dash_table.DataTable(
    #         id="recipe-builder-campaign-progress",
    #         columns=[
    #             {"name": "Set ID", "id": "set_id"},
    #             {"name": "Status", "id": "status"},
    #             {"name": "Timestamp", "id": "timestamp"},
    #             {"name": "Solution Pos", "id": "solution_pos"},
    #         ],
    #         data=[],  # Filled in via callback when a campaign is selected
    #         style_table={"overflowX": "auto"},
    #         style_cell={"textAlign": "center"},
    #         style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
    #     )
    # ], className="mb-4"),

    html.Hr(),
    html.H4("Optimizer Parameter Generation"),

    html.Div(id="bo-hyperparam-fields"),

    dbc.Row([
        dbc.Col([
            html.Label("Number of Batches"),
            dbc.Input(id="bo-num-batches", type="number", value=3, min=1)
        ], width=4),
        dcc.Interval(id="bo-generator-timer", interval=1000, n_intervals=0, disabled=True),
        dcc.Store(id="bo-generated-data", data=[]),

        dbc.Col([
            html.Label("Stopping Criterion"),
            dcc.Dropdown(
                id="bo-stopping-criterion",
                options=[
                    {"label": "Max Iterations", "value": "max_iter"},
                    # {"label": "Convergence (No Improvement)", "value": "no_improve"},
                    {"label": "Time Limit (minutes)", "value": "time_limit"},
                    # {"label": "Target Objective Reached", "value": "target_value"},
                ],
                placeholder="Select stopping rule"
            )
        ], width=4),

        dbc.Col([
            html.Label("Stopping Threshold"),
            dbc.Input(id="bo-stopping-value", type="number", placeholder="Enter threshold")
        ], width=4),
    ], className="mb-3"),

    dbc.Button("Generate Optimizer Parameters", id="bo-generate-btn", color="primary", className="mb-3"),
    html.Div(id="optimizer-output"),

    html.Div([
    dbc.Row([
            dbc.Col([
                dbc.Button("Pause", id="bo-pause-btn", color="warning", className="me-2"),
                html.Span("Status: ", style={"fontWeight": "bold"}),
                html.Span(id="bo-status-label", children="Idle")
            ])
        ], className="mb-3")
    ]),

    dcc.Store(id="bo-status-store", data="idle"),

    html.Div(id="bo-generated-table"),

    dbc.Button("Save Optimizer Parameters", id="bo-save-btn", color="success", className="mt-3", disabled=True),

    dbc.Alert(id="bo-save-alert", is_open=False, color="success", className="mt-3")

    ],
    className="container",
)

@callback(
    Output("optimizer-output", "children"),
    Input("bo-generate-btn", "n_clicks"),
    State("bo-num-batches", "value"),
    State("bo-stopping-criterion", "value"),
    State("bo-stopping-value", "value"),
    prevent_initial_call=True
)
def generate_optimizer_parameters(n_clicks, num_batches, stopping_criterion, stopping_value):
    import torch
    from optimizer import BayesianOptimizer, MockObjectiveFunction

    # Define search space bounds
    if n_clicks > 0:
        # bounds = torch.tensor([
        #     [0.1, 1.0],      # concentration
        #     [10.0, 100.0],   # print_speed
        #     [0.05, 0.5],     # gap_size
        #     [5.0, 25.0]      # volume
        # ]).T
        bounds = torch.tensor([
            [2, 20],      # concentration
            [50.0, 100.0],   # print_speed
            [0.01, 20],     # gap_size
            [6.0, 12.0]      # volume
        ]).T

        # Create optimizer and objective function
        optimizer = BayesianOptimizer(bounds=bounds, batch_size=num_batches)
        objective = MockObjectiveFunction()

        # Run optimization
        best_params, best_score = optimizer.optimize(
            objective_function=objective,
            n_iterations=stopping_value,
            n_initial_points=10
        )
        return html.Div([
            html.H3("Optimization Results:"),
            html.P(f"Best concentration: {best_params[0]:.4f}"),
            html.P(f"Best print speed: {best_params[1]:.4f}"),
            html.P(f"Best gap size: {best_params[2]:.4f}"),
            html.P(f"Best volume: {best_params[3]:.4f}"),
            html.P(f"Best score: {best_score:.4f}")
        ])

# @callback(
#     Output("bo-generator-timer", "disabled"),
#     Output("bo-generated-data", "data"),
#     Output("bo-generated-table", "children"),
#     Output("bo-save-btn", "disabled"),
#     Input("bo-generate-btn", "n_clicks"),
#     Input("bo-generator-timer", "n_intervals"),
#     State("bo-status-store", "data"),  # 🆕 check if paused
#     State("bo-generated-data", "data"),
#     State("bo-num-batches", "value"),
#     prevent_initial_call=True
# )
# def manage_bo_generation(n_clicks, n_intervals, status, current_data, num_batches):
#     import numpy as np
#     import pandas as pd
#     from dash import dash_table, callback_context

#     if current_data is None:
#         current_data = []

#     triggered = callback_context.triggered_id

#     if triggered == "bo-generate-btn":
#         # Reset state and begin generation
#         return False, [], dash.no_update, True

#     if triggered == "bo-generator-timer":
#         if status != "running":
#             # 🧊 paused or idle — stop timer activity
#             return dash.no_update, dash.no_update, dash.no_update, dash.no_update

#         if len(current_data) >= num_batches:
#             df = pd.DataFrame(current_data)
#             return True, current_data, dash_table.DataTable(
#                 columns=[{"name": i, "id": i} for i in df.columns],
#                 data=df.to_dict("records"),
#                 style_table={"overflowX": "auto"},
#                 page_size=10
#             ), False

#         # ➕ Generate one new row
#         new_row = {
#             "concentration": round(np.random.uniform(1, 5), 2),
#             "motor_speed": round(np.random.uniform(0.01, 20.0), 2),
#             "precursor_volume": round(np.random.uniform(6.0, 12.0), 2),
#         }

#         updated_data = current_data + [new_row]
#         df = pd.DataFrame(updated_data)

#         return False, updated_data, dash_table.DataTable(
#             columns=[{"name": i, "id": i} for i in df.columns],
#             data=df.to_dict("records"),
#             style_table={"overflowX": "auto"},
#             page_size=10
#         ), len(updated_data) < num_batches

#     return dash.no_update, dash.no_update, dash.no_update, dash.no_update

@callback(
    Output("bo-save-alert", "children"),
    Output("bo-save-alert", "is_open"),
    Input("bo-save-btn", "n_clicks"),
    prevent_initial_call=True
)
def save_bo_params(n):
    return "BO parameter sets saved successfully!", True
@callback(
    Output("bo-stopping-value", "placeholder"),
    Input("bo-stopping-criterion", "value")
)
def update_bo_stopping_placeholder(mode):
    if mode == "max_iter":
        return "e.g., 10 iterations"
    elif mode == "no_improve":
        return "e.g., 3 stagnant batches"
    elif mode == "time_limit":
        return "e.g., 30 minutes"
    return "Enter threshold"

# @callback(
#     Output("bo-status-store", "data"),
#     Output("bo-pause-btn", "children"),
#     Output("bo-status-label", "children"),
#     Input("bo-pause-btn", "n_clicks"),
#     Input("bo-generate-btn", "n_clicks"),
#     State("bo-status-store", "data"),
#     prevent_initial_call=True
# )
# def update_bo_status(pause_clicks, generate_clicks, current_status):
#     from dash import callback_context

#     triggered = callback_context.triggered_id

#     if triggered == "bo-generate-btn":
#         return "running", "Pause", "Running"

#     if triggered == "bo-pause-btn":
#         if current_status == "running":
#             return "paused", "Resume", "Paused"
#         elif current_status == "paused":
#             return "running", "Pause", "Running"

#     # fallback
#     return "idle", "Pause", "Idle"

# @callback(
#     Output("recipe-builder-campaign-progress", "data"),
#     Input("recipe-builder-campaign-dropdown", "value")
# )
# def update_campaign_progress(campaign_name):
#     if not campaign_name:
#         return []
#     return get_param_sets_for_campaign(campaign_name)
# def get_param_sets_for_campaign(campaign):
#     now = datetime.now()
#     statuses = ["Pending", "Generated", "Executed"]
#     return [
#         {
#             "set_id": f"PS{i+1}",
#             "status": 'Pending',
#             "timestamp": (now - timedelta(minutes=i*5)).strftime("%Y-%m-%d %H:%M"),
#             "solution_pos": 'A1',
#         }
#         for i in range(5)
#     ]