from dash import html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash
import io
import contextlib
from pymongo import MongoClient
import gridfs
import os
import signal

dash.register_page(
    __name__,
    path="/bayesian-optimization",
    name="Optimization",
    title="Optimization"
)

def emergency_stop():
    os.kill(os.getpid(), signal.SIGINT)

client = MongoClient('mongodb://aamp-user:b6b52bc6b85b8a53af21ae2883b3910d@aamp-mongodb-0.aamp.mmli1.ncsa.illinois.edu/aamp?replicaSet=aamp-mongodb&authSource=admin&tlsAllowInvalidCertificates=true&tls=true')
db = client['aamp']
fs = gridfs.GridFS(db)

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

layout = html.Div(
    [
        html.Div(id="bo-emergency-stop-output", style={"display": "none"}),
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
    ], className="mb-3"),

    dbc.ButtonGroup(
        [
            dbc.Button("Generate and Save Optimizer Parameters", id="bo-generate-btn", color="primary", className="mb-3"),
            dbc.Button("EMERGENCY STOP", id="bo-emergency-stop-btn", color="danger", className="mb-3")
        ],
    ),
    html.Pre(id="optimizer-output1", style={"whiteSpace": "pre-wrap", "border": "1px solid #ccc", "padding": "10px"}),

    ],
    className="container",
)

@callback(
    Output("bo-emergency-stop-output", "children"),
    Input("bo-emergency-stop-btn", "n_clicks"),
    prevent_initial_call=True
)
def emergency_stop_callback(n_clicks):
    emergency_stop()
    return []

@callback(
    Output("optimizer-output1", "children"),
    Input("bo-generate-btn", "n_clicks"),
    State("recipe-builder-campaign-dropdown", "value"),
    State("bo-batch-size", "value"),
    State("bo-target-objective", "value"),
    prevent_initial_call=True
)
def generate_optimizer_parameters(n_clicks, camp, bs, target_objective):
    import torch
    from Image_Processing.constrained_bo_ver2 import ConstrainedBayesianOptimizer

    f = io.StringIO()
    # plot_images = []
    with contextlib.redirect_stdout(f):
        # Define search space bounds
        if n_clicks > 0:
            collection = db['campaigns']
            entry = collection.find_one({"campaign_name": camp})
            grid_out = fs.find_one({"campaign_id": entry['_id'], "filename": "PProDOT_CB_Campaign_parameters.csv"})
            data = grid_out.read()
            # bounds = torch.tensor([
            #     [min(entry['concentration_range']), max(entry['concentration_range'])],      # concentration
            #     [min(entry['motor_speed']), max(entry['motor_speed'])],   # print_speed
            #     [min(entry['printing_gap']), max(entry['printing_gap'])],     # gap_size
            #     [min(entry['precursor_volume']), max(entry['precursor_volume'])]      # volume
            # ]).T
            bounds = torch.tensor([
                [0.01, 20.0],      # Speed
                [25.0, 107.0],     # Temperature
                [50, 200],         # Gap
                [5, 15]            # Volume
            ]).T

            discrete_points = [
                torch.tensor([0.1, 0.5, 0.7, 1.0]),  # Speed
                torch.tensor(list(range(25, 108))),  # Temperature
                torch.tensor(list(range(50, 201))),  # Gap
                torch.tensor(list(range(5, 16)))    # Volume
            ]

            # Create optimizer and objective function
            optimizer = ConstrainedBayesianOptimizer(
                bounds=bounds,
                csv_data=data,
                round_num=0,
                batch_size=bs,
                discrete_or_not=[False, True, True, True],
                discrete_points=discrete_points
            )
            print("\n\n")
            candidates, metadata = optimizer.suggest()
            
            collection = db['sets']
            for i in range(bs):
                set_doc = {
                    "campaign_id": entry['_id'],
                    "batch_no": optimizer.round_num,
                    "sample_no": i + 1,
                    "motor_speed": candidates[i][0].item(),
                    "temperature": candidates[i][1].item(),
                    "printing_gap": candidates[i][2].item(),
                    "precursor_volume": candidates[i][3].item(),
                    "ei_log": metadata["ei_log"][i],
                    "ei_raw": metadata["ei_raw"][i],
                    "p_valid": metadata["p_valid"][i],
                    "score_constrained": metadata["score_constrained"][i],
                    "source": metadata["source"][i],
                    "candidate_rank": metadata["candidate_rank"][i],
                    "mu_obj": metadata["mu_obj"][i],
                    "sigma_obj": metadata["sigma_obj"][i],
                    "mu_valid_raw": metadata["mu_valid_raw"][i],
                }
                collection.insert_one(set_doc)
            updated_df = optimizer.save_candidates_to_csv(candidates, metadata)
            fs.delete(grid_out._id)
            csv_bytes = updated_df.to_csv(index=False).encode('utf-8')
            fs.put(csv_bytes, filename="PProDOT_CB_Campaign_parameters.csv", campaign_id=entry['_id'])
            # for i, fig in enumerate(ff):
            #     experiment_id = entry['_id']
            #     buf = io.BytesIO()
            #     fig.savefig(buf, format="png")
            #     buf.seek(0)
            #     file_id = fs.put(buf.getvalue(), filename=f"sample_plot_{i}.png", metadata={"experiment_id": experiment_id})
            #     plots_collection = db['optimizer_plots']
            #     plot_doc = {
            #         "name": f"sample_matplotlib_plot_{i}",
            #         "experiment_id": experiment_id,
            #         "file_id": file_id
            #     }
            #     plots_collection.insert_one(plot_doc)
            # plot = plot_optimization_results(optimizer, objective)
            # plot_images.append(plot)
            # plot_images.append("plot")

            log_text = f.getvalue()

            # Create image components from the base64-encoded plot images
            # image_components = [html.Img(src=f"data:image/png;base64,{img}", style={"width": "100%"}) for img in plot_images]

            # Return the log text and plot images as components
            return log_text