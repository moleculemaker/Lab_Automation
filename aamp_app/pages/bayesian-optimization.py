from dash import html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash
import numpy as np
import pandas as pd
import io
import contextlib
import matplotlib.pyplot as plt
import base64

dash.register_page(
    __name__,
    path="/bayesian-optimization",
    name="Optimization",
    title="Optimization"
)

# def plot_optimization_results(optimizer, objective):
#     """Create selective plots of the optimization results (1, 3, and 4 only)."""

#     import matplotlib.pyplot as plt
#     import numpy as np
#     import base64
#     # import io

#     history = optimizer.get_optimization_history()
#     train_X, train_Y = optimizer.get_training_data()
#     true_params, _ = objective.get_optimal_parameters()
#     true_score = objective.evaluate_at_optimal()

#     # Create a 1x3 subplot layout for the three selected plots
#     fig, axes = plt.subplots(1, 3, figsize=(21, 6))  # Wider layout

#     ### 1. Optimization Progress (axes[0])
#     iterations = [h['iteration'] for h in history]
#     best_values = [h['best_value'] for h in history]

#     axes[0].plot(iterations, best_values, 'b-o', linewidth=2, markersize=6)
#     axes[0].axhline(y=true_score, color='r', linestyle='--', alpha=0.7, 
#                     label=f'True optimum: {true_score:.3f}')
#     axes[0].set_xlabel('Iteration')
#     axes[0].set_ylabel('Best Observed Value')
#     axes[0].set_title('Optimization Progress')
#     axes[0].legend()
#     axes[0].grid(True, alpha=0.3)

#     ### 3. Parameter Space Exploration (axes[1])
#     scatter = axes[1].scatter(train_X[:, 0], train_X[:, 1], c=train_Y.squeeze(), 
#                               cmap='viridis', alpha=0.6, s=50)
#     axes[1].scatter(optimizer.best_parameters[0], optimizer.best_parameters[1], 
#                     c='red', s=200, marker='*', label='Best found', 
#                     edgecolor='black', linewidth=2)
#     axes[1].scatter(true_params[0], true_params[1], c='orange', s=200, marker='*', 
#                     label='True optimum', edgecolor='black', linewidth=2)
#     axes[1].set_xlabel('Concentration')
#     axes[1].set_ylabel('Print Speed (mm/s)')
#     axes[1].set_title('Parameter Space Exploration')
#     axes[1].legend()
#     plt.colorbar(scatter, ax=axes[1], label='Objective Value')

#     ### 4. Gap Size vs Volume (axes[2])
#     scatter2 = axes[2].scatter(train_X[:, 2], train_X[:, 3], c=train_Y.squeeze(), 
#                                cmap='viridis', alpha=0.6, s=50)
#     axes[2].scatter(optimizer.best_parameters[2], optimizer.best_parameters[3], 
#                     c='red', s=200, marker='*', label='Best found', 
#                     edgecolor='black', linewidth=2)
#     axes[2].scatter(true_params[2], true_params[3], c='orange', s=200, marker='*', 
#                     label='True optimum', edgecolor='black', linewidth=2)
#     axes[2].set_xlabel('Gap Size (mm)')
#     axes[2].set_ylabel('Volume (μL)')
#     axes[2].set_title('🔍 Gap Size vs Volume')
#     axes[2].legend()
#     plt.colorbar(scatter2, ax=axes[2], label='Objective Value')

#     plt.tight_layout()
#     plt.show()

#     buf = io.BytesIO()
#     fig.savefig(buf, format="png", bbox_inches='tight')
#     buf.seek(0)
#     encoded_image = base64.b64encode(buf.read()).decode("utf-8")
#     buf.close()
#     plt.close(fig)

#     return encoded_image


# def plot_optimization_results(optimizer, objective):
#     """Create comprehensive plots of the optimization results."""
    
#     history = optimizer.get_optimization_history()
#     train_X, train_Y = optimizer.get_training_data()
#     true_params, _ = objective.get_optimal_parameters()
#     true_score = objective.evaluate_at_optimal()
    
#     # Create the visualization
#     fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
#     # 1. Optimization Progress
#     iterations = [h['iteration'] for h in history]
#     best_values = [h['best_value'] for h in history]
    
#     axes[0, 0].plot(iterations, best_values, 'b-o', linewidth=2, markersize=6)
#     axes[0, 0].axhline(y=true_score, color='r', linestyle='--', alpha=0.7, 
#                        label=f'True optimum: {true_score:.3f}')
#     axes[0, 0].set_xlabel('Iteration')
#     axes[0, 0].set_ylabel('Best Observed Value')
#     axes[0, 0].set_title('Optimization Progress')
#     axes[0, 0].legend()
#     axes[0, 0].grid(True, alpha=0.3)
    
#     # 2. Improvement Rate
#     # improvements = [best_values[i] - best_values[0] for i in range(len(best_values))]
#     # axes[0, 1].plot(iterations, improvements, 'g-o', linewidth=2, markersize=6)
#     # axes[0, 1].set_xlabel('Iteration')
#     # axes[0, 1].set_ylabel('Improvement from Initial')
#     # axes[0, 1].set_title('Cumulative Improvement')
#     # axes[0, 1].grid(True, alpha=0.3)
    
#     # 3. Parameter Space Exploration (Concentration vs Print Speed)
#     scatter = axes[0, 2].scatter(train_X[:, 0], train_X[:, 1], c=train_Y.squeeze(), 
#                                 cmap='viridis', alpha=0.6, s=50)
#     axes[0, 2].scatter(optimizer.best_parameters[0], optimizer.best_parameters[1], 
#                       c='red', s=200, marker='*', label='Best found', 
#                       edgecolor='black', linewidth=2)
#     axes[0, 2].scatter(true_params[0], true_params[1], c='orange', s=200, marker='*', 
#                       label='True optimum', edgecolor='black', linewidth=2)
#     axes[0, 2].set_xlabel('Concentration')
#     axes[0, 2].set_ylabel('Print Speed (mm/s)')
#     axes[0, 2].set_title('Parameter Space Exploration')
#     axes[0, 2].legend()
#     plt.colorbar(scatter, ax=axes[0, 2], label='Objective Value')
    
#     # 4. Gap Size vs Volume
#     scatter2 = axes[1, 0].scatter(train_X[:, 2], train_X[:, 3], c=train_Y.squeeze(), 
#                                  cmap='viridis', alpha=0.6, s=50)
#     axes[1, 0].scatter(optimizer.best_parameters[2], optimizer.best_parameters[3], 
#                       c='red', s=200, marker='*', label='Best found', 
#                       edgecolor='black', linewidth=2)
#     axes[1, 0].scatter(true_params[2], true_params[3], c='orange', s=200, marker='*', 
#                       label='True optimum', edgecolor='black', linewidth=2)
#     axes[1, 0].set_xlabel('Gap Size (mm)')
#     axes[1, 0].set_ylabel('Volume (μL)')
#     axes[1, 0].set_title('🔍 Gap Size vs Volume')
#     axes[1, 0].legend()
#     plt.colorbar(scatter2, ax=axes[1, 0], label='Objective Value')
    
#     # 5. Objective Value Distribution
#     # axes[1, 1].hist(train_Y.squeeze().numpy(), bins=20, alpha=0.7, color='skyblue', 
#     #                edgecolor='black')
#     # axes[1, 1].axvline(optimizer.best_observed_value, color='red', linestyle='--', 
#     #                   linewidth=2, label=f'Best: {optimizer.best_observed_value:.3f}')
#     # axes[1, 1].axvline(true_score, color='orange', linestyle='--', linewidth=2, 
#     #                   label=f'True: {true_score:.3f}')
#     # axes[1, 1].set_xlabel('Objective Value')
#     # axes[1, 1].set_ylabel('Frequency')
#     # axes[1, 1].set_title('Objective Value Distribution')
#     # axes[1, 1].legend()
#     # axes[1, 1].grid(True, alpha=0.3)
    
#     # 6. Parameter Convergence
#     # param_names = ['gap_size', 'volume']
#     # eval_order = np.arange(len(train_X))
    
#     # for i, name in enumerate(param_names):
#     #     color = plt.cm.Set1(i)
#     #     axes[1, 2].scatter(eval_order, train_X[:, i], alpha=0.6, s=30, 
#     #                       c=color, label=name)
#     #     axes[1, 2].axhline(y=true_params[i], color=color, linestyle='--', alpha=0.7)
    
#     # axes[1, 2].set_xlabel('Evaluation Order')
#     # axes[1, 2].set_ylabel('Parameter Value')
#     # axes[1, 2].set_title('Parameter Convergence')
#     # axes[1, 2].legend()
#     # axes[1, 2].grid(True, alpha=0.3)

#     plt.tight_layout()
#     plt.show()
    
#     buf = io.BytesIO()
#     fig.savefig(buf, format="png", bbox_inches='tight')
#     buf.seek(0)
#     encoded_image = base64.b64encode(buf.read()).decode("utf-8")
#     buf.close()
#     plt.close(fig)  # Close the figure to prevent it from showing

#     return encoded_image

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

    dbc.Row(
                    [
                        dbc.Col([html.H5("Select Parameters to Include")], width=5),
                    ],
                    className="mb-2",
    ),

    html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dcc.Dropdown(
                                    id="bo-params-dropdown",
                                    options=["Concentration", "Print Speed", "Gap Size", "Volume"],
                                    multi=True,
                                    value=["Concentration", "Print Speed", "Gap Size", "Volume"],
                                ),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
            ],
            id="bo-hyperparam-fields",
        ),
    
    dbc.Row([
        dbc.Col([
            html.Label("Batch Size"),
            dbc.Input(id="bo-batch-size", type="number", value=8, min=1)
        ], width=4),

        dbc.Col([
            html.Label("Target Objective (Required)"),
            dbc.Input(
                id="bo-target-objective",
                type="number",
                min=0,
                placeholder="e.g., 0.95"
            )
        ], width=4),

        # dbc.Col([
        #     html.Label("Number of Iterations (Required)"),
        #     dbc.Input(id="bo-maxiter", type="number", placeholder="e.g., 15", min=1)
        # ], width=4),
    ], className="mb-3"),

    dbc.Button("Generate and Save Optimizer Parameters", id="bo-generate-btn", color="primary", className="mb-3"),
    html.Pre(id="optimizer-output1", style={"whiteSpace": "pre-wrap", "border": "1px solid #ccc", "padding": "10px"}),

    ],
    className="container",
)

@callback(
    Output("optimizer-output1", "children"),
    Input("bo-generate-btn", "n_clicks"),
    State("bo-batch-size", "value"),
    State("bo-target-objective", "value"),
    # State("bo-maxiter", "value"),
    prevent_initial_call=True
)
def generate_optimizer_parameters(n_clicks, bs, target_objective):
    import torch
    from optimizer import BayesianOptimizer, MockObjectiveFunction

    f = io.StringIO()
    # plot_images = []
    with contextlib.redirect_stdout(f):
        # Define search space bounds
        if n_clicks > 0:
            bounds = torch.tensor([
                [0.1, 1.0],      # concentration
                [10.0, 100.0],   # print_speed
                [0.05, 0.5],     # gap_size
                [5.0, 25.0]      # volume
            ]).T
            # bounds = torch.tensor([
            #     [2, 20],      # concentration
            #     [0.01, 20],     # print_speed
            #     [50.0, 100.0],   # gap_size
            #     [6.0, 12.0]      # volume
            # ]).T

            # Create optimizer and objective function
            optimizer = BayesianOptimizer(bounds=bounds, batch_size=bs)
            objective = MockObjectiveFunction()

            # Run optimization
            best_params, best_score, plot_images = optimizer.optimize(
                objective_function=objective,
                n_iterations=200,
                n_initial_points=10,
                target=target_objective
            )
            print("\n\n")
            # plot = plot_optimization_results(optimizer, objective)
            # plot_images.append(plot)
            # plot_images.append("plot")

            log_text = f.getvalue()

            # Create image components from the base64-encoded plot images
            image_components = [html.Img(src=f"data:image/png;base64,{img}", style={"width": "100%"}) for img in plot_images]

            # Return the log text and plot images as components
            return image_components + [log_text]

# @callback(
#     Output("bo-generator-timer", "disabled"),
#     Output("bo-generated-data", "data"),
#     Output("bo-generated-table", "children"),
#     Output("bo-save-btn", "disabled"),
#     Input("bo-generate-btn", "n_clicks"),
#     Input("bo-generator-timer", "n_intervals"),
#     State("bo-status-store", "data"),  # 🆕 check if paused
#     State("bo-generated-data", "data"),
#     State("bo-batch-size", "value"),
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