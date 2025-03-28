from datetime import datetime
from command_sequence import CommandSequence
from command_invoker import CommandInvoker
import json
from devices.device import SerialDevice
import util
from mongodb_helper import MongoDBHelper
import dash
from dash import dcc
from dash import html
from dash import dash_table
import dash_ag_grid as dag
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
import os, signal
import inspect
from bson.objectid import ObjectId
from console_interceptor import ConsoleInterceptor
from gridfs import GridFS
import base64
import math
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import umap
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import gaussian_kde

from db.validation import solutions, films, devices, recipes
try:
    import serial.tools.list_ports
except ImportError:
    _has_serial = False
else:
    _has_serial = True
import typing

def load_env(file_path=".env"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

load_env()

mongo_uri = os.environ.get("MONGO_URI")
mongo_db_name = os.environ.get("MONGO_DB_NAME")

mongo = MongoDBHelper(
    mongo_uri,
    mongo_db_name,
)

try:
    db_list = mongo.client.list_database_names()
except Exception:
    print("Connection Failed. Try Again.")
    os.kill(os.getpid(), signal.SIGINT)
# with open("pw.txt", "w") as f:
#     f.write(mongo_username + "\n" + mongo_password)

print("\nreset complete")
com = CommandSequence()
invoker = CommandInvoker(com, log_to_file=True, log_filename="mylog.log")
invoker.clear_log_file()
invoker.invoking = False
if os.path.isfile("blank.yaml"):
    com.load_from_yaml("blank.yaml")
else:
    with open("blank.yaml", "w") as f:
        f.write(
            """- []
- []
- ALL"""
        )


# mongo = MongoDBHelper(
#     "mongodb+srv://"
#     + mongo_username
#     + ":"
#     + mongo_password
#     + "@mp3-cluster.rf3cato.mongodb.net/?retryWrites=true&w=majority",
#     "diaogroup",
# )
mongo_gridfs = GridFS(mongo.db, collection="recipes")
fs = GridFS(mongo.db)

solutions.init_collection()
devices.init_collection()
films.init_collection()
recipes.init_collection()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    prevent_initial_callbacks="initial_duplicate",
)
server = app.server

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Load", href="/load-recipe", external_link=True)),
        dbc.NavItem(dbc.NavLink("View", href="/view-recipe", external_link=True)),
        dbc.NavItem(dbc.NavLink("Code", href="/edit-recipe", external_link=True)),
        dbc.NavItem(dbc.NavLink("Doc", href="/data", external_link=True)),
        dbc.NavItem(dbc.NavLink("Execute", href="/execute-recipe", external_link=True)),
        dbc.NavItem(
            dbc.NavLink("Manual Control", href="/manual-control", external_link=True)
        ),
        dbc.NavItem(dbc.NavLink("DB Browser", href="/database", external_link=True)),
        # dbc.NavItem(dbc.NavLink("Options", href="/options", external_link=True)),
        dbc.NavItem(
            dbc.NavLink("Real Time", href="/real-time-telemetry", external_link=True)
        ),
        # dbc.NavItem(dbc.NavLink("Images", href="/images", external_link=True)),
        dbc.NavItem(dbc.NavLink("Sampler", href="/sampler", external_link=True)),
        # dbc.DropdownMenu(
        #     children=[
        #         # dbc.DropdownMenuItem(
        #         #     "Load Recipe", href="/load-recipe", external_link=True
        #         # ),
        #         dbc.DropdownMenuItem(
        #             "Real Time Telemetry",
        #             href="/real-time-telemetry",
        #             external_link=True,
        #         ),
        #         dbc.DropdownMenuItem(
        #             "Edit Code", href="/edit-recipe", external_link=True
        #         ),
        #         dbc.DropdownMenuItem("Document", href="/data", external_link=True),
        #         # dbc.DropdownMenuItem("Options", href="/options", external_link=True),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="Tools",
        # ),
    ],
    brand="AAMP",
    brand_href="/",
    color="primary",
    dark=True,
    id="navbar",
    className="mb-3",
)


app.layout = html.Div([dcc.Location(id="url"), navbar, dash.page_container])


@app.callback(Output("navbar", "brand"), Input("url", "pathname"))
def print_pagename(url):  # all pages
    print("loading: " + url + "\n")
    return "AAMP"


def update_upstream_recipe_dict():
    if not hasattr(com, 'document'):
        # create_new_recipe_doc(n, "/load-recipe", "testfile")
        com.document = {
            '_id': ObjectId(),
            'file_name': 'testfile',
            'recipe_dict': {
                'devices': [],
                'commands': [],
                'execution_options': []
            },
            'dash_friendly': True,
            'executions': []
        }
    recipe_dict = com.get_recipe()
    com.document['recipe_dict'] = {
        'devices': recipe_dict[0],
        'commands': recipe_dict[1],
        'execution_options': recipe_dict[2]
    }
    mongo.db['recipes'].update_one(
        {'_id': com.document['_id']}, 
        {'$set': com.document}, 
        upsert=True
    )
    return True



def update_execution_upstream(execution):
    if "document" in list(com.__dict__.keys()):
        com.document["executions"].append(execution)
        mongo.db["recipes"].update_one(
            {"_id": com.document["_id"]}, {"$set": com.document}
        )
        print("successfully updated execution upstream")
        return True
    else:
        print("com.document not found")
        return False
    
#  TODO: include where the log was generated from
def save_log_to_mongo(log_string):
    """Save a log entry to the MongoDB logs collection."""
    try:
        log_entry = {
            "timestamp": f"Recipe_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "log": log_string,
        }
        mongo.db["logs"].insert_one(log_entry)  # Save to 'logs' collection
        print("Log saved to MongoDB successfully.")
    except Exception as e:
        print(f"Failed to save log to MongoDB: {e}")

# ---------------------------------------------------
# Home Page
# ---------------------------------------------------


@app.callback(
    Output("home-recipes-list-table", "data"),
    [Input("home-refresh-list-button", "n_clicks")],
    # prevent_initial_call=True,
)
def fetch_recipe_list(n_clicks):  # homepage
    docs = mongo.find_documents("recipes", {})
    docs = mongo.db["recipes"].find(
        {},
        {
            "_id": 0,
            "file_name": 1,
            "posix_friendly": 1,
            "dash_friendly": 1,
            "python_code": 1,
        },
    )
    print("fetch_recipe_list")
    data = []
    for doc in reversed(list(docs)):
        file_name = doc.get("file_name", "")
        posix_friendly = doc.get("posix_friendly", True)
        dash_friendly = doc.get("dash_friendly", False)
        if "python_code" in doc:
            python_code = True
        else:
            python_code = False
        data.append(
            {
                "file_name": file_name,
                "posix_friendly": posix_friendly,
                "dash_friendly": dash_friendly,
                "python_code": python_code,
            }
        )
    return data


@app.callback(
    Output("filename-input", "value"),
    Input("home-recipes-list-table", "active_cell"),
    [State("url", "pathname"), State("home-recipes-list-table", "data")],
    # prevent_initial_call=True,
)
def fill_filename_input(active_cell, url, data):  # homepage
    if str(url) == "/load-recipe":
        if active_cell is not None:
            print("fill_filename_input")
            return data[active_cell["row"]]["file_name"]
        if "document" in list(com.__dict__.keys()):
            print("fill_filename_input")
            return com.document["file_name"]
        return ""


@app.callback(
    [
        Output("home-load-file-alert", "is_open"),
        Output("home-load-file-alert", "children"),
        Output("home-load-file-alert", "color"),
        Output("home-load-file-alert", "duration"),
    ],
    [Input("filename-input-button", "n_clicks")],
    [State("filename-input", "value")],
    prevent_initial_call=True,
)
def get_document_from_db(n_clicks, filename):  # homepage
    print("get_document_from_db")
    if filename is not None and filename != "":
        # Extract the YAML content from the document
        document = mongo.find_documents("recipes", {"file_name": filename})[0]
        invoker.clear_log_file()
        try:
            com.clear_recipe()
            com.load_from_dict(document["recipe_dict"])
            com.document = document
            print("loaded from dict")
            return [True, "Recipe loaded", "success", 10000]

        except Exception as e:
            print("Failed load from dict: " + str(e))
        if os.name == "posix":
            if "posix_friendly" in document and not document["posix_friendly"]:
                return [
                    True,
                    "This recipe is not compatible with your system (POSIX compatability error)",
                    "danger",
                    8000,
                ]
        if (
            document.get("dash_friendly", "") == False
            or document.get("python_code", "") == ""
        ):
            yaml_content = document.get("yaml_data", "")
            # Update the YAML output
            with open("to_load.yaml", "w") as file:
                file.write(yaml_content)
            com.load_from_yaml("to_load.yaml")
            com.document = document
            return [True, "Recipe loaded", "success", 10000]
        else:
            exec(document.get("python_code", ""))
            com.load_from_yaml("to_save.yaml")
            com.document = document

        # com.python_code = document.get("python_code", "")

        return [True, "Recipe loaded", "success", 10000]

    return [True, "No recipe selected", "warning", 3000]


@app.callback(
    [
        Output("home-load-file-alert", "is_open", allow_duplicate=True),
        Output("home-load-file-alert", "children", allow_duplicate=True),
        Output("home-load-file-alert", "color", allow_duplicate=True),
        Output("home-load-file-alert", "duration", allow_duplicate=True),
    ],
    Input("home-create-new-recipe-button", "n_clicks"),
    [State("url", "pathname"), State("filename-input", "value")],
    prevent_initial_call=True,
)
def create_new_recipe_doc(n, url, name):
    if str(url) == "/load-recipe":
        print("create_new_recipe_doc")
        name = f"Recipe_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mongo.db["recipes"].insert_one(
            {
                "file_name": name,
                "recipe_dict": {
                    "devices": [],
                    "commands": [],
                    "execution_options": {
                        "output_files": [],
                        "default_execution_record_name": "Execution - " + str(name),
                    },
                },
                "dash_friendly": True,
                "executions": [],
            }
        )
        fetch_recipe_list(1)
        return [True, "Recipe created", "success", 10000]


# ---------------------------------------------------
# View Recipe Page
# ---------------------------------------------------

@app.callback(
    Output("devices-table-div", "children"),
    [Input("refresh-button1", "n_clicks"), Input("devices-table", "data")],
    [State("devices-table-div", "children")],
)
def update_device_table(n_clicks, data, table):
    print("update_device_table")
    
    table_data1 = com.get_clean_device_list().copy()
    table_data1_new = [
        {
            "index": index,
            "device_type": device[0],
            "params": str(device[1]),
        }
        for index, device in enumerate(table_data1)
    ]

    column_defs = [
        {"headerName": "Index", "field": "index"},
        {"headerName": "Device Type", "field": "device_type", "rowDrag": True},
        {"headerName": "Parameters", "field": "params", "flex": 1},
    ]

    grid = dag.AgGrid(
        id="devices-table",
        columnDefs=column_defs,
        rowData=table_data1_new,
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        dashGridOptions={
            "rowDragManaged": True,
            "animateRows": True,
            "rowSelection": "single",
        },
        style={"height": 400, "width": "100%"},
    )

    return html.Div(grid)



@app.callback(
    Output("commands-table", "data"),
    Input("save-command-editor", "n_clicks"),
    [
        State("commands-table", "active_cell"),
        State("commands-table", "data"),
        State("command-json-editor", "value"),
    ],
    prevent_initial_call=True,
)
def save_command(n_clicks, active_cell, data, value):  # view-recipe page
    print("save_command")
    if active_cell is not None and data[active_cell["row"]]["params"] != str(
        json.loads(value)
    ):
        com.command_list[data[active_cell["row"]]["index"]][0]._params = eval(value)
        update_upstream_recipe_dict()
        return None
    return data


@app.callback(
    [
        Output("devices-table", "data"),
        Output("view-recipe-alert", "is_open", allow_duplicate=True),
        Output("view-recipe-alert", "children", allow_duplicate=True),
        Output("view-recipe-alert", "color", allow_duplicate=True),
        Output("view-recipe-alert", "duration", allow_duplicate=True),
    ],
    [
        Input("save-device-editor", "n_clicks"),
        Input("devices-table", "data")
    ],
    [
        State("devices-table", "active_cell"),
        State("devices-table", "data"),
        State("device-json-editor", "value"),
    ],
    prevent_initial_call=True,
)
def save_device(n_clicks, updated_data, active_cell, data, value):  # view-recipe page
    print("save_device")
    if active_cell is not None and data[active_cell["row"]]["params"] != str(
        json.loads(value)
    ):
        # data_row = data[active_cell["row"]]
        params = eval(value)
        com.device_by_name[params["name"]].update_init_args(params)
        update_success = update_upstream_recipe_dict()
        return None, True, "Device updated.", "success", 3000
    return data, False, "Something went wrong. Device not updated.", "danger", 3000


@app.callback(
    Output("command-json-editor", "value"),
    [Input("command-editor-modal", "is_open")],
    [State("commands-table", "active_cell"), State("commands-table", "data")],
    prevent_initial_call=True,
)
def fill_command_json_editor(is_open, active_cell, data):  # view-recipe page
    if active_cell is not None and is_open:
        print("fill_command_json_editor")
        return json.dumps(eval(data[active_cell["row"]]["params"]), indent=4)

    return ""


@app.callback(
    Output("add-device-dropdown", "options"),
    [Input("device-add-modal", "is_open")],
    [State("devices-table", "active_cell"), State("devices-table", "data")],
    prevent_initial_call=True,
)
def fill_device_add_modal(is_open, active_cell, data):  # view-recipe page
    print("fill_device_add_modal")
    return list(util.devices_ref_redundancy.keys())


@app.callback(
    [Output("add-device-json-editor", "value")],
    [Input("add-device-dropdown", "value"), Input("device-add-modal", "is_open")],
    prevent_initial_call=True,
)
def fill_device_add_json_editor(value, is_open):  # view-recipe page
    print("fill_device_add_json_editor")
    if not is_open or value is None:
        return [""]
    # args_list = inspect.getfullargspec(util.devices_ref_redundancy[value]['obj'].__init__).args
    args_dict = {}
    # for arg in args_list:
    #     if arg != "self" and arg != "name":
    #         args_dict[arg] = None
    #     if arg == "name":
    #         args_dict[arg] = value
    args_list = list(util.devices_ref_redundancy[value]["init"]["args"].keys())
    for arg in args_list:
        args_dict[arg] = util.devices_ref_redundancy[value]["init"]["args"][arg][
            "default"
        ]
    return [(json.dumps(args_dict, indent=4))]


@app.callback(
    [
        Output("device-json-editor", "value"),
        Output("edit-device-serial-ports-info", "children"),
    ],
    [Input("device-editor-modal", "is_open")],
    [State("devices-table", "active_cell"), State("devices-table", "data")],
    prevent_initial_call=True,
)
def fill_device_json_editor(is_open, active_cell, data):  # view-recipe page
    print("fill_device_json_editor")
    if active_cell is not None and is_open:
        if _has_serial and isinstance(
            com.device_by_name[eval(data[active_cell["row"]]["params"])["name"]],
            SerialDevice,
        ):
            ports = serial.tools.list_ports.comports()
            str_ports = ""
            for port, desc, hwid in sorted(ports):
                str_ports += f"{port}: {desc} [{hwid}]\n"
            lines = str_ports.splitlines()
            device_port_html = [
                html.Div(["COM Port Info:"], style={"fontWeight": "bold"})
            ]
            device_port_html.append(html.Div([html.Div(line) for line in lines]))
        else:
            device_port_html = ""
        return (
            json.dumps(eval(data[active_cell["row"]]["params"]), indent=4),
            device_port_html,
        )
    return "", ""


@app.callback(
    [
        Output("save-command-editor", "disabled"),
        Output("edit-command-error", "children"),
    ],
    Input("command-json-editor", "value"),
    State("command-editor-modal", "is_open"),
    prevent_initial_call=True,
)
def enable_save_command_button(value, is_open):  # view-recipe page
    if not is_open:
        return False, ""
    try:
        parsed_json = json.loads(value)
        if parsed_json["delay"] < 0:
            return True, "Delay must be greater than or equal to 0"
        print("enable_save_command_button")
        return False, ""
    except Exception as e:
        if type(e) == json.decoder.JSONDecodeError:
            return True, "Invalid JSON"
        return True, str(type(e))


@app.callback(
    [Output("save-device-editor", "disabled"), Output("edit-device-error", "children")],
    Input("device-json-editor", "value"),
    State("device-editor-modal", "is_open"),
    prevent_initial_call=True,
)
def enable_save_device_button(value, is_open):  # view-recipe page
    if not is_open:
        return False, ""
    try:
        parsed_json = json.loads(value)
        print("enable_save_device_button")
        return False, ""
    except Exception as e:
        if type(e) == json.decoder.JSONDecodeError:
            return True, "Invalid JSON"
        return True, str(type(e))


@app.callback(
    [Output("add-device-editor", "disabled"), Output("add-device-error", "children")],
    [Input("add-device-json-editor", "value"), Input("add-device-dropdown", "value")],
    State("device-add-modal", "is_open"),
    prevent_initial_call=True,
)
def enable_add_device_button(value, device_type, is_open):  # view-recipe page
    if value == "":
        return True, "No device selected"
    if not is_open:
        return False, ""
    try:
        sig = inspect.signature(util.named_devices[device_type].__init__)
        args = {}
        for param in sig.parameters.values():
            arg_type = param.annotation
            args[param.name] = (
                typing.get_args(arg_type)[0]
                if typing.get_origin(arg_type) is typing.Union
                else arg_type
            )
        parsed_json = json.loads(value)
        for key in parsed_json:
            # print("\n" + key)
            # print(
            #     "input: "
            #     + str(type((parsed_json[key])))
            #     + ", expected: "
            #     + str(args[key])
            # )
            if type((parsed_json[key])) != args[key]:
                return False, f"Invalid type for {key}. Expected {str(args[key])}"
            # if not isinstance(parsed_json[key], args[key]):
            #     return True, f"Invalid type for {key}. Expected {str(args[key])}"
        print("enable_add_device_button")
        return False, ""
    except Exception as e:
        if type(e) == json.decoder.JSONDecodeError:
            return True, "Invalid JSON"
        return False, str(type(e))


@app.callback(
    [
        Output("view-recipe-alert", "is_open"),
        Output("view-recipe-alert", "children"),
        Output("view-recipe-alert", "color"),
        Output("view-recipe-alert", "duration"),
    ],
    [Input("add-device-editor", "n_clicks")],
    [
        State("add-device-dropdown", "value"),
        State("url", "pathname"),
        State("add-device-json-editor", "value"),
    ],
    prevent_initial_call=True,
)
def view_recipe_add_device(n, device_type, url, device_dict):
    if str(url) == "/view-recipe":
        com.add_device_from_dict(device_type, json.loads(device_dict))
        update_success = update_upstream_recipe_dict()
        return (
            True,
            f"Added {device_type}. Database updated: {update_success}",
            "success",
            3000,
        )


@app.callback(
    Output("edit-command-button", "disabled"),
    Input("commands-table", "active_cell"),
)
def edit_command_button(table_div_children):  # view-recipe page
    active_cell = table_div_children
    if active_cell is not None:
        print("edit_command_button")
        return False
    else:
        return True


@app.callback(
    Output("edit-device-button", "disabled"),
    Input("devices-table", "active_cell"),
)
def edit_device_button(table_div_children):  # view-recipe page
    active_cell = table_div_children
    if active_cell is not None:
        return False
    else:
        return True


@app.callback(
    Output("delete-device-button", "disabled"),
    Input("devices-table", "active_cell"),
)
def view_recipe_enable_delete_device_button(table_div_children):
    active_cell = table_div_children
    if active_cell is not None:
        return False
    else:
        return True


@app.callback(
    Output("delete-command-button", "disabled"), Input("commands-table", "active_cell")
)
def view_recipe_enable_delete_command_button(table_div_children):
    active_cell = table_div_children
    if active_cell is not None:
        return False
    else:
        return True


@app.callback(
    Output("devices-table", "data", allow_duplicate=True),
    Input("delete-device-button", "n_clicks"),
    [
        State("url", "pathname"),
        State("devices-table", "active_cell"),
        State("devices-table", "data"),
    ],
    prevent_initial_call=True,
)
def view_recipe_delete_device(n, url, active_cell, data):
    if str(url) == "/view-recipe":
        com.remove_device_by_index(data[active_cell["row"]]["index"])
        update_success = update_upstream_recipe_dict()
        return None


@app.callback(
    Output("commands-table", "data", allow_duplicate=True),
    Input("delete-command-button", "n_clicks"),
    [
        State("url", "pathname"),
        State("commands-table", "active_cell"),
        State("commands-table", "data"),
    ],
    prevent_initial_call=True,
)
def view_recipe_delete_command(n, url, active_cell, data):
    if str(url) == "/view-recipe":
        com.remove_command(data[active_cell["row"]]["index"])
        update_success = update_upstream_recipe_dict()
        return None


@app.callback(
    Output("commands-table-div", "children"),
    [Input("refresh-button2", "n_clicks"), Input("commands-table", "data")],
    [State("commands-table-div", "children")],
)
def update_commands_table(n_clicks, data, table):  # view-recipe page
    print("update_commands_table")
    command_list = com.command_list.copy()
    command_params = []
    for index, command in enumerate(command_list):
        temp_dict_command_params = {"command": type(command[0]).__name__}
        temp_dict_command_params.update(
            {"params": str(command[0].get_init_args()), "index": index}
        )
        command_params.append((temp_dict_command_params))
        # else:
        #     command_params.append(command._params)

    table_data2 = command_params
    # add_command_accordian(0, to_add=[dbc.AccordionItem("new new", title="new new", item_id="new new")])

    table = dash_table.DataTable(
        id="commands-table",
        data=table_data2,
        columns=[
            {"name": "Index", "id": "index"},
            {"name": "Command", "id": "command"},
            {"name": "Parameters", "id": "params"},
        ],
        style_cell={
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "maxWidth": 0,
            "textAlign": "left",
            "padding": "5px",
        },
        style_cell_conditional=[
            {"if": {"column_id": "index"}, "width": "5%"},
            {"if": {"column_id": "command"}, "width": "20%"},
            {"if": {"column_id": "params"}, "width": "70%"},
        ],
        # tooltip_data=[
        #     {
        #         column: {"value": str(value), "type": "markdown"}
        #         for column, value in row.items()
        #     }
        #     for row in table_data2
        # ],
        # tooltip_duration=None,
        # editable = True,
    )
    return table


@app.callback(
    Output("view-recipe-command-add-modal", "is_open"),
    Input("add-command-open-modal-button", "n_clicks"),
    [State("url", "pathname")],
    prevent_initial_call=True,
)
def view_recipe_open_add_command_modal(n, url):
    if url == "/view-recipe":
        return True


@app.callback(
    Output("view-recipe-add-command-device-dropdown", "options"),
    Input("view-recipe-command-add-modal", "is_open"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def view_recipe_fill_add_command_device_dropdown(is_open, url):
    if url == "/view-recipe":
        print("view_recipe_fill_add_command_device_dropdown")
        return list(util.devices_ref_redundancy.keys())


@app.callback(
    Output("view-recipe-add-command-command-dropdown", "options"),
    Input("view-recipe-add-command-device-dropdown", "value"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def view_recipe_fill_add_command_command_dropdown(device_type, url):
    if url == "/view-recipe":
        if device_type is None or device_type == "":
            return []
        return list(util.devices_ref_redundancy[device_type]["commands"].keys())


@app.callback(
    Output("view-recipe-add-command-json-editor", "value"),
    Input("view-recipe-add-command-command-dropdown", "value"),
    [
        State("url", "pathname"),
        State("view-recipe-add-command-device-dropdown", "value"),
    ],
    prevent_initial_call=True,
)
def view_recipe_fill_add_command_json_editor(command_type, url, device_type):
    if url == "/view-recipe":
        if command_type is None or command_type == "":
            return ""
        args_dict = {}
        args_list = util.devices_ref_redundancy[device_type]["commands"][command_type][
            "args"
        ]
        for arg in args_list:
            args_dict[arg] = args_list[arg]["default"]
        args_dict["delay"] = 0.0
        return json.dumps(args_dict, indent=4)


@app.callback(
    [
        Output("view-recipe-add-command-editor", "disabled"),
        Output("add-command-error", "children"),
    ],
    Input("view-recipe-add-command-json-editor", "value"),
    State("url", "pathname"),
)
def view_recipe_check_add_command_json(value, url):
    if str(url) == "/view-recipe":
        if value == "" or value is None:
            return True, []
        try:
            json.loads(value)
            return False, []
        except Exception as e:
            return True, ["Invalid JSON: " + str(e)]


@app.callback(
    [
        Output("view-recipe-command-add-modal", "is_open", allow_duplicate=True),
        Output("view-recipe-alert", "is_open", allow_duplicate=True),
        Output("view-recipe-alert", "children", allow_duplicate=True),
        Output("view-recipe-alert", "color", allow_duplicate=True),
        Output("view-recipe-alert", "duration", allow_duplicate=True),
        Output("commands-table", "data", allow_duplicate=True),
    ],
    Input("view-recipe-add-command-editor", "n_clicks"),
    [
        State("url", "pathname"),
        State("view-recipe-add-command-device-dropdown", "value"),
        State("view-recipe-add-command-command-dropdown", "value"),
        State("view-recipe-add-command-json-editor", "value"),
    ],
    prevent_initial_call=True,
)
def view_recipe_add_command(n, url, device_type, command_type, json_value):
    if str(url) == "/view-recipe":
        if json_value == "" or json_value is None:
            return [False, True, ["Something went wrong"], "danger", 3000]
        try:
            com.add_command_from_dict(device_type, command_type, json.loads(json_value))
            update_upstream_recipe_dict()
            return [False, True, ["Command added"], "success", 3000, None]
        except Exception as e:
            print(str(e))
            return [
                False,
                True,
                ["Something went wrong: " + str(e)],
                "danger",
                3000,
                None,
            ]


@app.callback(
    [
        Output("view-recipe-execution-options-output-files", "value"),
        Output("view-recipe-execution-options-default-execution-record-name", "value"),
    ],
    Input("url", "pathname"),
)
def view_recipe_fill_execution_options(url):
    if str(url) == "/view-recipe":
        if "document" in com.__dict__.keys():
            try:
                ls = com.document["recipe_dict"]["execution_options"]["output_files"]
            except Exception as e:
                print(str(e))
                ls = []
            filesToRet = ""
            for item in ls:
                filesToRet += item + "\n"
            return [
                filesToRet,
                com.document["recipe_dict"]["execution_options"][
                    "default_execution_record_name"
                ],
            ]
        return ["", ""]


@app.callback(
    [
        Output("view-recipe-execution-options-saved-label", "children"),
        Output("view-recipe-execution-options-saved-label", "style"),
    ],
    Input("view-recipe-execution-options-save-button", "n_clicks"),
    [
        State("view-recipe-execution-options-output-files", "value"),
        State("view-recipe-execution-options-default-execution-record-name", "value"),
        State("url", "pathname"),
    ],
    prevent_initial_call=True,
)
def view_recipe_save_execution_options(
    n, filenames, default_execution_record_name, url
):
    if str(url) == "/view-recipe":
        if filenames is not None:
            com.execution_options["output_files"] = filenames.splitlines()
        com.execution_options[
            "default_execution_record_name"
        ] = default_execution_record_name
        success = update_upstream_recipe_dict()
        if success:
            return ["Saved!", {"display": "block"}]
        else:
            return ["Something went wrong", {"display": "block"}]
    return ["", {"display": "none"}]


# ---------------------------------------------------
# Python Edit Recipe Page
# ---------------------------------------------------


@app.callback(
    [
        Output("ace-recipe-editor", "value", allow_duplicate=True),
        Output("ace-editor-alert", "is_open"),
        Output("ace-editor-alert", "children"),
        Output("ace-editor-alert", "color"),
        Output("ace-editor-alert", "duration"),
    ],
    [Input("refresh-button-ace", "n_clicks")],
    State("url", "pathname"),
    # prevent_initial_call=True,
)
def fill_ace_editor(n, url):  # python-edit-recipe page
    if url == "/edit-recipe":
        if hasattr(com, "document"):
            python_code = com.document.get("python_code", "")
            if python_code is not None and python_code != "":
                print("fill_ace_editor")
                return [str(python_code), True, "Loaded!", "success", 1500]
            else:
                print("fill_ace_editor")
                return ["", True, "No code available", "warning", 1000]
        else:
            return ["", True, "No code available", "warning", 1000]
    else:
        return ["", False, "na", "success", 0]


@app.callback(
    [
        Output("ace-recipe-editor", "value", allow_duplicate=True),
        Output("ace-editor-alert", "is_open", allow_duplicate=True),
        Output("ace-editor-alert", "children", allow_duplicate=True),
        Output("ace-editor-alert", "color", allow_duplicate=True),
        Output("ace-editor-alert", "duration", allow_duplicate=True),
    ],
    Input("execute-and-save-button", "n_clicks"),
    [State("ace-recipe-editor", "value")],
    prevent_initial_call=True,
)
def execute_and_save(n, value):  # python-edit-recipe page
    print("execute_and_save")
    if value is not None and value != "":
        try:
            exec(value)
            doc_id = com.document.get("_id", "")
            (mongo.update_yaml_file("recipes", doc_id, {"python_code": value}))
            com.load_from_yaml("to_save.yaml")
            com.document = mongo.find_documents("recipes", {"_id": doc_id})[0]
            return [str(value), True, "Saved!", "success", 1500]
        except Exception as e:
            return [str(value), True, str(e), "danger", 5000]
    else:
        return ["", True, "No code to execute", "warning", 1000]

    # return ["", False, "", "success", 1500]


@app.callback(
    [
        Output("add-device-dropdown-ace", "options"),
        Output("add-device-dropdown-ace", "value"),
    ],
    [Input("device-add-modal-ace", "is_open")],
    prevent_initial_call=True,
)
def fill_device_add_modal_ace(is_open):  # python-edit-recipe page
    if is_open:
        print("fill_device_add_modal_ace")
        return list(util.devices_ref_redundancy.keys()), ""
    return [], ""


@app.callback(
    [
        Output("add-command-device-dropdown-ace", "options"),
        Output("add-command-device-dropdown-ace", "value"),
    ],
    [Input("command-add-modal-ace", "is_open")],
    prevent_initial_call=True,
)
def fill_command_device_add_modal_ace(is_open):  # python-edit-recipe page
    if is_open:
        print("fill_command_device_add_modal_ace")
        return list(util.devices_ref_redundancy.keys()), ""
    return [], ""


@app.callback(
    [
        Output("add-command-command-dropdown-ace", "options"),
        Output("add-command-command-dropdown-ace", "value"),
    ],
    [Input("add-command-device-dropdown-ace", "value")],
    prevent_initial_call=True,
)
def fill_command_add_modal_ace(device):  # python-edit-recipe page
    if device is not None and device != "":
        print("fill_command_add_modal_ace")
        return list(util.devices_ref_redundancy[device]["commands"].keys()), ""
    return [], ""


@app.callback(
    Output("add-device-editor-ace", "disabled"),
    [
        Input("add-device-dropdown-ace", "value"),
        Input("device-add-modal-ace", "is_open"),
    ],
    State("device-add-modal-ace", "is_open"),
    prevent_initial_call=True,
)
def enable_add_device_button_ace(value, is_openInp, is_open):  # python-edit-recipe page
    if value == "" or value is None:
        return True
    print("enable_add_device_button_ace")
    return False


@app.callback(
    Output("add-command-editor-ace", "disabled"),
    [
        Input("add-command-command-dropdown-ace", "value"),
        Input("command-add-modal-ace", "is_open"),
    ],
    State("command-add-modal-ace", "is_open"),
    prevent_initial_call=True,
)
def enable_add_command_button_ace(
    value, is_openInp, is_open
):  # python-edit-recipe page
    if value == "" or value is None:
        return True
    print("enable_add_command_button_ace")
    return False


@app.callback(
    [
        Output("ace-recipe-editor", "value"),
        Output("ace-editor-alert", "is_open", allow_duplicate=True),
        Output("ace-editor-alert", "children", allow_duplicate=True),
        Output("ace-editor-alert", "color", allow_duplicate=True),
        Output("ace-editor-alert", "duration", allow_duplicate=True),
    ],
    Input("add-device-editor-ace", "n_clicks"),
    [State("ace-recipe-editor", "value"), State("add-device-dropdown-ace", "value")],
    prevent_initial_call=True,
)
def add_device_to_recipe_ace(n_clicks, value, device_type):  # python-edit-recipe page
    print("add_device_to_recipe_ace")
    if value == "" or value is None:
        return ["", True, "No code in editor", "warning", 3000]
    try:
        value = str(value)
        import_line = util.devices_ref_redundancy[device_type]["import_device"]
        init_line = util.devices_ref_redundancy[device_type]["init"]["default_code"]
        if import_line not in value:
            value = import_line + "\n" + value
        value = value.replace(
            "##################################################\n##### Add commands to the command sequence",
            "seq.add_device("
            + init_line
            + ")\n\n##################################################\n##### Add commands to the command sequence",
        )
        return [str(value), True, "Device added successfully", "success", 3000]
    except Exception as e:
        print(e)
        return [str(value), True, "Error adding device: " + str(e), "danger", 6000]


@app.callback(
    [
        Output("ace-recipe-editor", "value", allow_duplicate=True),
        Output("ace-editor-alert", "is_open", allow_duplicate=True),
        Output("ace-editor-alert", "children", allow_duplicate=True),
        Output("ace-editor-alert", "color", allow_duplicate=True),
        Output("ace-editor-alert", "duration", allow_duplicate=True),
    ],
    Input("add-command-editor-ace", "n_clicks"),
    [
        State("ace-recipe-editor", "value"),
        State("add-command-command-dropdown-ace", "value"),
        State("add-command-device-dropdown-ace", "value"),
    ],
    prevent_initial_call=True,
)
def add_commands_to_recipe_ace(
    n_clicks, value, command, device_type
):  # python-edit-recipe page
    print("add_commands_to_recipe_ace")
    og_value = str(value)
    if value == "" or value is None:
        return ["", True, "No code in editor", "warning", 3000]
    try:
        value = str(value)
        command_line = util.devices_ref_redundancy[device_type]["commands"][command][
            "default_code"
        ]
        import_line = util.devices_ref_redundancy[device_type]["import_commands"]
        import_device_line = util.devices_ref_redundancy[device_type]["import_device"]
        if import_device_line not in value:
            raise Exception(
                "Device (or its import '"
                + import_device_line
                + "') not found in recipe"
            )
        if import_line not in value:
            value = import_line + "\n" + value
        if "\nrecipe_file = 'to_save.yaml'\nseq.save_to_yaml(recipe_file)" not in value:
            raise Exception("Code is not in valid format")
        value = value.replace(
            "\nrecipe_file = 'to_save.yaml'\nseq.save_to_yaml(recipe_file)",
            "\nseq.add_command("
            + command_line
            + ")\n\n\nrecipe_file = 'to_save.yaml'\nseq.save_to_yaml(recipe_file)",
        )
        return [str(value), True, "Command added successfully", "success", 3000]
    except Exception as e:
        print(e)
        return [og_value, True, str("Error adding command: " + str(e)), "danger", 6000]


# ---------------------------------------------------
# Execute Recipe Page
# ---------------------------------------------------


def kill_execution():  # execute-recipe page
    os.kill(os.getpid(), signal.SIGINT)


@app.callback(
    Output("hidden-div", "children"),
    Input("stop-button", "n_clicks"),
    prevent_initial_call=True,
)
def stop_execution(n):  # execute-recipe page
    print("stop_execution")
    kill_execution()
    return []


@app.callback(
    Output("execute-recipe-output", "children"),
    [Input("execute-button", "n_clicks")],
    prevent_initial_call=True,
)
def execute_recipe(n_clicks):  # execute-recipe page
    print("execute_recipe")
    invoker.invoking = True
    invoker.invoke_commands()
    invoker.invoking = False
    return ["done"]


@app.callback(
    Output("console-out2", "children"),
    Input("interval1", "n_intervals"),
    [State("url", "pathname")],
    prevent_initial_call=True,
)
def update_output(n, url):  # execute-recipe page
    if url == "/execute-recipe":
        log_string = ""
        log_list = invoker.get_log_messages()
        for msg in log_list:
            log_string += msg
            # log_string += '<br>'
        return html.Pre(log_string)
    return ""


@app.callback(
    Output("console-out2", "children", allow_duplicate=True),
    Input("reset-button", "n_clicks"),
    prevent_initial_call=True,
)
def reset_console(n):  # execute-recipe page
    print("reset_console")
    invoker.clear_log_file()
    # dashLoggerHandler.queue = []
    return []


@app.callback(
    [
        Output("execute-recipe-upload-document", "value"),
        Output("execute-recipe-upload-name", "value"),
    ],
    Input("reset-button", "n_clicks"),
    State("url", "pathname"),
)
def execute_recipe_load_document_viewer(n, url):
    if str(url) == "/execute-recipe":
        if "document" in list(com.__dict__.keys()):
            if com.device_list != []:
                toRet = ""
                recipe_ec = com.get_recipe()
                for device in recipe_ec[0]:
                    toRet += str(device) + "\n"
                toRet += "\n"
                for command in recipe_ec[1]:
                    toRet += str(command) + "\n"
                if "default_execution_record_name" in list(
                    com.execution_options.keys()
                ):
                    return [
                        toRet,
                        com.execution_options["default_execution_record_name"],
                    ]
                return [toRet, "Execution"]
        return ["", "No Recipe Loaded"]


@app.callback(
    [Output("execute-recipe-upload-data-output", "children")],
    Input("execute-recipe-upload-data-button", "n_clicks"),
    [
        State("url", "pathname"),
        State("execute-recipe-upload-name", "value"),
        State("execute-recipe-upload-document", "value"),
        State("console-out2", "children"),
        State("execute-recipe-upload-notes", "value"),
        State("execute-recipe-upload-files", "contents"),
        State("execute-recipe-upload-files", "filename"),
    ],
    prevent_initial_call=True,
)
def execute_recipe_upload_data(
    n_clicks, url, name, recipe_data, console_log, notes, files, filenames
):
    if str(url) == "/execute-recipe":
        print("execute_recipe_upload_data")
        execution = {}
        execution["name"] = name
        if (
            isinstance(recipe_data, list)
            and recipe_data is not None
            and recipe_data != []
        ):
            execution["recipe"] = recipe_data[0].split("\n")
        elif recipe_data is not None and recipe_data != "":
            execution["recipe"] = recipe_data.split("\n")
        execution["notes"] = notes
        execution["log"] = str(console_log["props"]["children"]).split("\n")
        execution["files"] = []
        if isinstance(files, list):
            for i, file in enumerate(files):
                # print(file)
                file_bytes = base64.b64decode(file + "==")
                execution["files"].append(
                    mongo_gridfs.put(file_bytes, filename=filenames[i])
                )
        exec_success = update_execution_upstream(execution)
        # exec_success = False
        if exec_success:
            return [html.P("Data uploaded successfully")]
        else:
            return [html.P("Error uploading data")]


# ---------------------------------------------------
# Data Page
# ---------------------------------------------------


def render_dict(data):  # data (and maybe database) page
    if isinstance(data, dict):
        return [
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            html.Div(
                                render_dict(value),
                                style={"margin-left": "15px"},
                            )
                        ],
                        title=key,
                    )
                    for key, value in data.items()
                ]
            )
        ]
    else:
        return html.P(str(data))


@app.callback(
    Output("data-output-div2", "children"),
    Input("load-data-button", "n_clicks"),
    prevent_initial_call=True,
)
def load_data_accordion(n):  # data page
    if not hasattr(com, "document"):
        print("load_data_accordion - no document")
        return []
    print("load_data_accordion")
    return render_dict(com.document)


# ---------------------------------------------------
# Manual Control Recipe Page
# ---------------------------------------------------


@app.callback(
    Output("manual-control-device-dropdown", "options"),
    Input("interval-manual-control", "n_intervals"),
    State("url", "pathname"),
)
def fill_manual_control_device_dropdown(n, url):  # manual-control page
    if str(url) == "/manual-control":
        print("fill_manual_control_device_dropdown")
        return list(util.devices_ref_redundancy.keys())


@app.callback(
    [
        Output("manual-control-command-dropdown", "disabled"),
        Output("manual-control-command-dropdown", "options"),
    ],
    Input("manual-control-device-dropdown", "value"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def fill_manual_control_command_dropdown(val, url):  # manual-control page
    if str(url) == "/manual-control":
        print("fill_manual_control_command_dropdown")
        if val is None or val == "":
            return [True, []]
        else:
            if util.devices_ref_redundancy[val]["serial"] == False:
                return [
                    False,
                    list(util.devices_ref_redundancy[val]["commands"].keys()),
                ]
            else:
                toRet = list(util.devices_ref_redundancy[val]["commands"].keys()).copy()
                for command in util.devices_ref_redundancy[val]["serial_sequence"]:
                    if command in toRet:
                        toRet.remove(command)
                return [False, toRet]


@app.callback(
    [Output("manual-control-device-form", "children")],
    Input("manual-control-device-dropdown", "value"),
    State("url", "pathname"),
)
def create_manual_control_device_form(value, url):
    if str(url) == "/manual-control":
        print("create_manual_control_device_form")
        if value is None or value == "":
            return [[]]
        else:
            args = util.devices_ref_redundancy[value]["init"]["args"]
            toRet = []
            for arg in args:
                if arg == "port":
                    toRet.append(
                        dbc.Row(
                            [
                                dbc.Label(
                                    dbc.NavLink(
                                        arg,
                                        n_clicks=0,
                                        id="manual-control-port-field",
                                        style={
                                            "cursor": "pointer",
                                            "color": "blue",
                                            "textDecoration": "underline",
                                        },
                                    ),
                                    html_for=str(value + "+" + arg),
                                    width=2,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Input(
                                            id=str(value + "+" + arg),
                                            value=args[arg]["default"],
                                            placeholder=args[arg]["notes"],
                                        ),
                                    ],
                                    width=10,
                                ),
                            ],
                            className="mb-2",
                        )
                    )
                else:
                    toRet.append(
                        dbc.Row(
                            [
                                dbc.Label(
                                    [arg], html_for=str(value + "+" + arg), width=2
                                ),
                                dbc.Col(
                                    [
                                        dbc.Input(
                                            id=str(value + "+" + arg),
                                            value=args[arg]["default"],
                                            placeholder=args[arg]["notes"],
                                        ),
                                    ],
                                    width=10,
                                ),
                            ],
                            className="mb-2",
                        )
                    )

            return [toRet]


@app.callback(
    [Output("manual-control-command-form", "children")],
    [
        Input("manual-control-command-dropdown", "value"),
        Input("manual-control-device-dropdown", "value"),
    ],
    [
        State("url", "pathname"),
        State("manual-control-device-form", "children"),
    ],
)
def create_manual_control_command_form(command, device, url, device_form):
    if str(url) == "/manual-control":
        print("create_manual_control_command_form")
        if command is None or command == "" or device is None or device == "":
            return [[]]
        else:
            toRet = []
            if util.devices_ref_redundancy[device]["serial"] == True:
                seq_toRet = []
                for seq_command in util.devices_ref_redundancy[device][
                    "serial_sequence"
                ]:
                    seq_toRet.append(dbc.Row([dbc.Label([seq_command])]))
                    args = util.devices_ref_redundancy[device]["commands"][seq_command][
                        "args"
                    ]
                    for arg in args:
                        seq_toRet.append(
                            dbc.Row(
                                [
                                    dbc.Label(
                                        [arg],
                                        html_for=str(
                                            device + "+" + seq_command + "+" + arg
                                        ),
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Input(
                                                id=str(
                                                    device
                                                    + "+"
                                                    + seq_command
                                                    + "+"
                                                    + arg
                                                ),
                                                value=args[arg]["default"],
                                                placeholder=args[arg]["notes"],
                                            ),
                                        ],
                                        width=10,
                                    ),
                                ],
                                className="mb-2",
                            )
                        )
                toRet.append(dbc.Row(seq_toRet, className="mb-3"))
            toRet.append(dbc.Row([dbc.Label([command])]))
            args = util.devices_ref_redundancy[device]["commands"][command]["args"]
            com_toRet = []
            for arg in args:
                com_toRet.append(
                    dbc.Row(
                        [
                            dbc.Label(
                                [arg],
                                html_for=str(device + command + "+" + arg),
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Input(
                                        id=str(device + command + "+" + arg),
                                        value=args[arg]["default"],
                                        placeholder=args[arg]["notes"],
                                    ),
                                ],
                                width=10,
                            ),
                        ],
                        className="mb-2",
                    )
                )
            toRet.append(dbc.Row(com_toRet, className="mb-3"))
            return [toRet]


@app.callback(
    Output("manual-control-device-dropdown", "value"),
    Input("manual-control-clear-button", "n_clicks"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def manual_control_clear_form(n, url):
    if str(url) == "/manual-control":
        print("manual_control_clear_form")
        return None


@app.callback(
    Output("manual-control-clear-button", "disabled"),
    Input("manual-control-device-dropdown", "value"),
    State("url", "pathname"),
)
def manual_control_clear_button(value, url):
    if str(url) == "/manual-control":
        print("manual_control_clear_button")
        if value is None or value == "":
            return True
        else:
            return False


@app.callback(
    Output("manual-control-open-execute-modal-button", "disabled"),
    Input("manual-control-command-dropdown", "value"),
    State("url", "pathname"),
)
def manual_control_execute_button(value, url):
    if str(url) == "/manual-control":
        print("manual_control_execute_button")
        if value is None or value == "":
            return True
        else:
            return False


@app.callback(
    [
        Output("manual-control-execute-modal", "is_open", allow_duplicate=True),
        Output("manual-control-execute-modal-body", "children", allow_duplicate=True),
    ],
    Input("manual-control-open-execute-modal-button", "n_clicks"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def open_manual_control_execute_modal(n, url):
    if str(url) == "/manual-control":
        print("open_manual_control_execute_modal")
        return True, []


@app.callback(
    [
        Output("manual-control-command-dropdown", "className"),
        Output("manual-control-alert", "is_open", allow_duplicate=True),
        Output("manual-control-alert", "children", allow_duplicate=True),
        Output("manual-control-alert", "color", allow_duplicate=True),
        Output("manual-control-alert", "duration", allow_duplicate=True),
        Output(
            "manual-control-execute-modal-body-code", "children", allow_duplicate=True
        ),
    ],
    Input("manual-control-open-execute-modal-button", "n_clicks"),
    [
        State("url", "pathname"),
        State("manual-control-command-dropdown", "className"),
        State("manual-control-device-dropdown", "value"),
        State("manual-control-command-dropdown", "value"),
        State("manual-control-device-form", "children"),
        State("manual-control-command-form", "children"),
    ],
    prevent_initial_call=True,
)
def manual_control_execute_fill_code(
    n, url, opt, device, command, device_form, command_form
):
    if str(url) == "/manual-control":
        print("manual_control_execute_fill_code")
        if device is None or device == "" or command is None or command == "":
            return (
                opt,
                True,
                "Something went wrong. Check the fields below.",
                "danger",
                3000,
            )
        code = ""
        code += util.devices_ref_redundancy[device]["import_device"]
        code += "\n"
        code += util.devices_ref_redundancy[device]["import_commands"]
        code += "\n"
        code += "from command_sequence import CommandSequence\nfrom command_invoker import CommandInvoker\n"

        instantiate_code = ""
        instantiate_code += util.devices_ref_redundancy[device]["init"]["obj_name"]
        instantiate_code += "("
        for i, arg in enumerate(util.devices_ref_redundancy[device]["init"]["args"]):
            if i != 0:
                instantiate_code += ", "
            instantiate_code += arg + "="
            if util.devices_ref_redundancy[device]["init"]["args"][arg]["type"] == str:
                instantiate_code += "'"
                instantiate_code += str(
                    device_form[i]["props"]["children"][1]["props"]["children"][0][
                        "props"
                    ]["value"]
                )
                instantiate_code += "'"
            else:
                instantiate_code += str(
                    device_form[i]["props"]["children"][1]["props"]["children"][0][
                        "props"
                    ]["value"]
                )
        instantiate_code += ")"
        code += str(device) + "_seq" + " = CommandSequence()"
        code += "\n\n"
        code += str(device) + "_seq" + ".add_device(" + instantiate_code + ")"
        code += "\n"

        if util.devices_ref_redundancy[device]["serial"] == True:
            for i, serial_seq_command in enumerate(
                util.devices_ref_redundancy[device]["serial_sequence"]
            ):
                code += (
                    str(device)
                    + "_seq"
                    + ".add_command("
                    + str(serial_seq_command)
                    + "("
                )
                for ii, serial_seq_command_arg in enumerate(
                    util.devices_ref_redundancy[device]["commands"][serial_seq_command][
                        "args"
                    ]
                ):
                    if ii != 0:
                        code += ", "
                    if serial_seq_command_arg == "receiver":
                        code += (
                            serial_seq_command_arg
                            + "="
                            + str(device)
                            + "_seq.device_by_name['"
                            + str(
                                command_form[0]["props"]["children"][(2 * ii) + 1][
                                    "props"
                                ]["children"][1]["props"]["children"][0]["props"][
                                    "value"
                                ]
                            )
                            + "']"
                        )
                    elif (
                        util.devices_ref_redundancy[device]["commands"][
                            serial_seq_command
                        ]["args"][serial_seq_command_arg]["type"]
                        == str
                    ):
                        code += (
                            serial_seq_command_arg
                            + "="
                            + "'"
                            + str(
                                command_form[0]["props"]["children"][(2 * ii) + 1][
                                    "props"
                                ]["children"][1]["props"]["children"][0]["props"][
                                    "value"
                                ]
                            )
                            + "'"
                        )
                    else:
                        code += (
                            serial_seq_command_arg
                            + "="
                            + str(
                                command_form[0]["props"]["children"][(2 * ii) + 1][
                                    "props"
                                ]["children"][1]["props"]["children"][0]["props"][
                                    "value"
                                ]
                            )
                        )

                code += "))\n"
            code += str(device) + "_seq" + ".add_command(" + str(command) + "("
            for ii, seq_command_arg in enumerate(
                util.devices_ref_redundancy[device]["commands"][command]["args"]
            ):
                if ii != 0:
                    code += ", "
                if seq_command_arg == "receiver":
                    code += (
                        seq_command_arg
                        + "="
                        + str(device)
                        + "_seq.device_by_name['"
                        + str(
                            command_form[2]["props"]["children"][ii]["props"][
                                "children"
                            ][1]["props"]["children"][0]["props"]["value"]
                        )
                        + "']"
                    )
                elif (
                    util.devices_ref_redundancy[device]["commands"][command]["args"][
                        seq_command_arg
                    ]["type"]
                    == str
                ):
                    code += (
                        seq_command_arg
                        + "="
                        + "'"
                        + str(
                            command_form[2]["props"]["children"][ii]["props"][
                                "children"
                            ][1]["props"]["children"][0]["props"]["value"]
                        )
                        + "'"
                    )
                else:
                    code += (
                        seq_command_arg
                        + "="
                        + str(
                            command_form[2]["props"]["children"][ii]["props"][
                                "children"
                            ][1]["props"]["children"][0]["props"]["value"]
                        )
                    )

            code += "))\n\n"
        else:
            code += str(device) + "_seq" + ".add_command(" + str(command) + "("
            for ii, seq_command_arg in enumerate(
                util.devices_ref_redundancy[device]["commands"][command]["args"]
            ):
                if ii != 0:
                    code += ", "
                if seq_command_arg == "receiver":
                    code += (
                        seq_command_arg
                        + "="
                        + str(device)
                        + "_seq.device_by_name['"
                        + str(
                            command_form[1]["props"]["children"][ii]["props"][
                                "children"
                            ][1]["props"]["children"][0]["props"]["value"]
                        )
                        + "']"
                    )
                elif (
                    util.devices_ref_redundancy[device]["commands"][command]["args"][
                        seq_command_arg
                    ]["type"]
                    == str
                ):
                    code += (
                        seq_command_arg
                        + "="
                        + "'"
                        + str(
                            command_form[1]["props"]["children"][ii]["props"][
                                "children"
                            ][1]["props"]["children"][0]["props"]["value"]
                        )
                        + "'"
                    )
                else:
                    code += (
                        seq_command_arg
                        + "="
                        + str(
                            command_form[1]["props"]["children"][ii]["props"][
                                "children"
                            ][1]["props"]["children"][0]["props"]["value"]
                        )
                    )

            code += "))\n\n"
        code += (
            str(device)
            + "_seq_invoker = CommandInvoker("
            + str(device)
            + "_seq, False, False, False)\n"
        )
        code += str(device) + "_seq_invoker.invoke_commands()"
        interceptor = ConsoleInterceptor()
        print("\n")
        interceptor.start_interception()
        print(code)
        interceptor.stop_interception()
        code_output = interceptor.get_intercepted_messages()
        del interceptor
        code_log_string = ""
        for msg in code_output:
            code_log_string += msg
        # interceptor = ConsoleInterceptor()
        # interceptor.start_interception()
        # try:
        # exec(code)
        # interceptor.stop_interception()
        # messages = interceptor.get_intercepted_messages()
        # log_string = ""
        # for msg in messages:
        #     if msg == '\r':
        #         log_string += '\n'
        #     else:
        #         log_string += msg
        # print(messages)

        save_log_to_mongo(code_log_string)
        
        return (
            opt,
            True,
            "Command(s) ready to execute.",
            "warning",
            0,
            html.Pre(code_log_string),
        )
        # except Exception as e:
        #     print(e)
        #     # interceptor.stop_interception()
        #     # messages = interceptor.get_intercepted_messages()
        #     # log_string = ""
        #     # for msg in messages:
        #     #     log_string += msg
        #     return opt, True, "Something went wrong. Check logs.", "Warning", 0, True, html.Pre(code_log_string)

    return opt


@app.callback(
    [
        Output("manual-control-alert", "is_open"),
        Output("manual-control-alert", "children"),
        Output("manual-control-alert", "color"),
        Output("manual-control-alert", "duration"),
        Output("manual-control-execute-modal-body", "children"),
    ],
    [Input("manual-control-execute-button", "n_clicks")],
    [
        State("url", "pathname"),
        State("manual-control-execute-modal-body-code", "children"),
    ],
    prevent_initial_call=True,
)
def manual_control_execute_code(n, url, code):
    if str(url) == "/manual-control":
        print("manual_control_execute_code")
        interceptor = ConsoleInterceptor()
        # print('\n')
        # interceptor.start_interception()
        # print(code)
        # interceptor.stop_interception()
        # code_output = interceptor.get_intercepted_messages()
        # code_log_string = ""
        # for msg in code_output:
        #     code_log_string += msg
        # interceptor = ConsoleInterceptor()
        interceptor.start_interception()
        try:
            exec(code["props"]["children"])
            interceptor.stop_interception()
            messages = interceptor.get_intercepted_messages()
            del interceptor
            log_string = ""
            for msg in messages:
                if msg == "\r":
                    log_string += "\n"
                else:
                    log_string += msg
            return True, "Execution complete.", "success", 0, html.Pre(log_string)
        except Exception as e:
            print(e)
            interceptor.stop_interception()
            messages = interceptor.get_intercepted_messages()
            del interceptor
            log_string = ""
            for msg in messages:
                log_string += msg
            return (
                True,
                "Something went wrong. Check logs.",
                "danger",
                0,
                html.Pre(log_string),
            )
    return False, "", "success", 0, html.Pre("")


@app.callback(
    [
        Output("manual-control-port-modal", "is_open"),
        Output("manual-control-serial-ports-info", "children"),
    ],
    Input("manual-control-port-field", "n_clicks"),
    prevent_initial_call=True,
)
def open_fill_manual_control_serial(n):
    if _has_serial and n != 0:
        ports = serial.tools.list_ports.comports()
        str_ports = ""
        for port, desc, hwid in sorted(ports):
            str_ports += f"{port}: {desc} [{hwid}]\n"
        lines = str_ports.splitlines()
        return True, [html.Div([html.Div(line) for line in lines])]
    return False, []


# ---------------------------------------------------------------
# Database page
# ---------------------------------------------------------------


@app.callback(
    Output("database-db-dropdown", "options"),
    Input("interval-database", "n_intervals"),
    State("url", "pathname"),
)
def fill_database_db_dropdown(n, url):
    if str(url) == "/database":
        print("fill_database_db_dropdown")
        # temporary provision to not expose other databases in demos
        return [x for x in list(mongo.client.list_database_names()) if x == "aamp_test"]


@app.callback(
    [
        Output("database-collection-dropdown", "disabled"),
        Output("database-collection-dropdown", "options"),
    ],
    [Input("database-db-dropdown", "value")],
    State("url", "pathname"),
    prevent_initial_call=True,
)
def fill_database_collection_dropdown(db, url):  # database page
    if str(url) == "/database":
        print("fill_database_collection_dropdown")
        if db is not None and db != "":
            return False, list(mongo.client[db].list_collection_names())
    return True, []


@app.callback(
    [
        Output("database-document-dropdown", "disabled"),
        Output("database-document-dropdown", "options"),
    ],
    Input("database-collection-dropdown", "value"),
    [State("url", "pathname"), State("database-db-dropdown", "value")],
    prevent_initial_call=True,
)
def fill_database_document_dropdown(collection, url, db):
    if str(url) == "/database":
        if collection is not None and collection != "":
            print("fill_database_document_dropdown")
            docs = list(mongo.client[db][collection].find({}))
            toRet = []
            for doc in docs:
                toRet.append(str(doc["_id"]))
            return False, toRet
        else:
            return True, []


def process_schema(schema):
    if isinstance(schema, dict):
        if "bsonType" not in list(schema.keys()):
            for key in list(schema.keys()):
                schema[key] = process_schema(schema[key])
        elif "bsonType" in list(schema.keys()):
            schema["Properties"] = {"Data Type": schema["bsonType"]}
            del schema["bsonType"]
            if "description" in list(schema.keys()):
                schema["Properties"].update({"Description": schema["description"]})
                del schema["description"]
            if "required" in list(schema.keys()):
                # schema['Properties'].update({"Required": schema['required']})
                del schema["required"]
            if "properties" in list(schema.keys()):
                schema["Variables"] = process_schema(schema["properties"])
                del schema["properties"]
            if "title" in list(schema.keys()):
                del schema["title"]

    return schema


@app.callback(
    Output("database-collection-schema", "children"),
    [
        Input("database-collection-dropdown", "value"),
        Input("database-db-dropdown", "value"),
    ],
    [State("url", "pathname")],
    prevent_initial_call=True,
)
def fill_database_collection_schema(collection, db, url):
    if str(url) == "/database":
        print("fill_database_collection_schema")
        if collection is not None and collection != "" and db is not None and db != "":
            try:
                print("Colln info:")
                print(mongo.client[db].get_collection(collection))
                options = mongo.client[db].get_collection(collection).options()
                if "validator" in options:
                    schema = options["validator"]
                    schema = process_schema(schema)
                    return render_dict(schema)
                else:
                    return [""]
            except Exception as e:
                print(f"Error retrieving schema: {e}")
                return ["Validation rules missing or something went wrong."]

    return []


@app.callback(
    Output("database-document-viewer", "children"),
    [
        Input("database-document-dropdown", "value"),
        Input("database-collection-dropdown", "value"),
    ],
    [State("url", "pathname"), State("database-db-dropdown", "value")],
    prevent_initial_call=True,
)
def fill_database_document_viewer(document, collection, url, db):
    if str(url) == "/database":
        print("fill_database_document_viewer")
        if document is not None and document != "" and db is not None and db != "":
            # try:
            doc = mongo.client[db][collection].find({"_id": ObjectId(document)})[0]
            return render_dict(doc)
            # except Exception as e:
            #     return ["Document missing or something went wrong"]
    return []


# ---------------------------------------------------------------
# Real Time Telemetry page
# ---------------------------------------------------------------
import random


@app.callback(
    [Output("real-time-telemetry-div", "children")],
    [
        Input("real-time-telemetry-device-dropdown", "value"),
        Input("interval-real-time-telemetry", "n_intervals"),
    ],
    [State("url", "pathname")],
    prevent_initial_call=True,
)
def fill_real_time_telemetry(device, n, url):
    if str(url) == "/real-time-telemetry" and device is not None and device != "":
        print("fill_real_time_telemetry")
        if "telemetry" in list(util.devices_ref_redundancy[device].keys()):
            device_parameter_options = util.devices_ref_redundancy[device]["telemetry"][
                "options"
            ]
            telemetry_data = {}
            for parameter in util.devices_ref_redundancy[device]["telemetry"][
                "parameters"
            ]:
                parameter_options = util.devices_ref_redundancy[device]["telemetry"][
                    "parameters"
                ][parameter]
                telemetry_data[parameter] = getattr(
                    util.devices_ref_redundancy[device]["default_obj"],
                    parameter_options["function_name"],
                )()
            telemetry_data["rand"] = random.randint(1, 10)

            metrics_data = telemetry_data

            metrics_cards = []
            for metric_name, metric_value in metrics_data.items():
                card = dbc.Card(
                    dbc.CardBody(
                        [
                            html.H5(metric_name, className="card-title"),
                            html.P(
                                f"{metric_value}",
                                className="card-text",
                                style={"fontSize": "1.25rem"},
                            ),
                        ]
                    ),
                    className="mb-3",
                    style={"width": "30%"},
                )
                metrics_cards.append(card)

            return [
                dbc.Row(
                    children=metrics_cards,
                    id="metrics-row",
                    style={"justifyContent": "space-around"},
                )
            ]
            return [str(telemetry_data)]
        return [""]
    return [""]

# ---------------------------------------------------------------
# Images page
# ---------------------------------------------------------------

@app.callback(
    Output("images-alert", "children"),
    Output("images-alert", "is_open"),
    Output("images-alert", "color"),
    Input("upload-image-button", "n_clicks"),
    [
        State("sample-number", "value"),
        State("motor-speed", "value"),
        State("temperature", "value"),
        State("concentration", "value"),
        State("printing-gap", "value"),
        State("precursor-volume", "value"),
        State("solvent", "value"),
        State("image-upload", "contents"),
    ],
    prevent_initial_call=True,
)
def upload_image(n_clicks, sample_number, motor_speed, temperature, concentration, printing_gap, precursor_volume, solvent, image_contents):
    print("upload_image")
    if not image_contents:
        return (
            "No image uploaded. Please upload an image.",
            True,
            "danger",
        )

    try:
        header, encoded = image_contents.split(",", 1)
        image_data = base64.b64decode(encoded)

        image_id = fs.put(image_data, filename=f"sample_{sample_number}.png")

        metadata = {
            "sample_number": sample_number,
            "motor_speed": motor_speed,
            "temperature": temperature,
            "concentration": concentration,
            "printing_gap": printing_gap,
            "precursor_volume": precursor_volume,
            "solvent": solvent,
            "image_id": str(image_id), 
            "timestamp": datetime.utcnow(),
        }
        mongo.db["images"].insert_one(metadata)

        return (
            f"Image uploaded successfully with ID: {image_id}",
            True,
            "success",
        )
    except Exception as e:
        print(f"Error uploading image: {e}")
        return (
            f"Failed to upload image. Error: {str(e)}",
            True,
            "danger",
        )


# ---------------------------------------------------------------
# Sampler page
# ---------------------------------------------------------------

# add the following to the temp choices d and c
# when adding to d, make sure to add three or four options evenly spaced between the min and max
# when adding to c, make sure to just add the min and max values

# "1,4-Dichlorobenzene",C1=CC(=CC=C1Cl)Cl��,25,153.548
# "1,2,4-Trihlorobenzene",C1=CC(=C(C=C1Cl)Cl)Cl,25,184.946
# o-xylene,CC1=CC=CC=C1C��,25,119.5683
# m-xylene,CC1=CC(=CC=C1)C,25,114.5912
# p-xylene,CC1=CC=C(C=C1)C,25,113.775
# mesitylene,CC1=CC(=CC(=C1)C)C,25,139.1875
# toluene,CC1=CC=CC=C1�,25,87.7163
# 1-Chloronaphthalene,C1=CC=C2C(=C1)C=CC=C2Cl,25,227.995
# anisole,COC1=CC=CC=C1�,25,129.1316
# Tetrahydrofuran,C1CCOC1��,25,45.7105
# decane,CCCCCCCCCC,25,148.3072

# Add these constants from initial_point_generator.py
SOLV_NAMES = ["CF", "CB", "CB9:A1", "CB8:A2", "CB7:A3", "1,4-Dichlorobenzene", "1,2,4-Trihlorobenzene", "o-xylene", "m-xylene", "p-xylene", "mesitylene", "toluene", "1-Chloronaphthalene", "anisole", "Tetrahydrofuran", "decane"]
CONCEN_D = [2, 5, 10, 15, 20]
PRINT_GAP_D = [50, 100]
PREC_VOL_D = [6, 9, 12]
MOTOR_SPEEDS_D = [0.01, 0.0355, 0.126, 0.4472, 1.587, 5.635, 20]
SPEED_C = (0.01, 20.0)
PREC_VOL_C = (6.0, 12.0)
CONCEN_C = (1, 5)

TEMP_CHOICES_D = {
    "CF": [25, 41.3], 
    "CB": [25, 47.3, 62.9, 87.6, 107.4], 
    "CB9:A1": [25, 47.3, 62.9, 87.6, 107.4],
    "CB8:A2": [25, 47.3, 62.9, 87.6, 107.4], 
    "CB7:A3": [25, 47.3, 62.9, 87.6, 107.4],
    "1,4-Dichlorobenzene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "1,2,4-Trihlorobenzene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "o-xylene": [25, 47.3, 62.9, 87.6, 107.4, 119.6],
    "m-xylene": [25, 47.3, 62.9, 87.6, 107.4, 114.6],
    "p-xylene": [25, 47.3, 62.9, 87.6, 107.4, 113.8],
    "mesitylene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "toluene": [25, 47.3, 55.1, 62.9, 75.1, 87.7],
    "1-Chloronaphthalene": [25, 47.3, 62.9, 87.6, 107.4, 135],
    "anisole": [25, 47.3, 62.9, 87.6, 107.4, 129.1],
    "Tetrahydrofuran": [25, 30.1, 35.4, 40, 45.7],
    "decane": [25, 47.3, 62.9, 87.6, 107.4, 135],
}

TEMP_CHOICES_C = {
    "CF": (25, 41.3),
    "CB": (25, 107.4),
    "CB9:A1": (25, 107.4),
    "CB8:A2": (25, 107.4),
    "CB7:A3": (25, 107.4),
    "1,4-Dichlorobenzene": (25, 135),
    "1,2,4-Trihlorobenzene": (25, 135),
    "o-xylene": (25, 119.6),
    "m-xylene": (25, 114.6),
    "p-xylene": (25, 113.8),
    "mesitylene": (25, 135),
    "toluene": (25, 87.7),
    "1-Chloronaphthalene": (25, 135),
    "anisole": (25, 129.1),
    "Tetrahydrofuran": (25, 45.7),
    "decane": (25, 135),
}

# adding custom discrete parameter options
@app.callback(
    Output({"type": "sampler-dropdown", "id": MATCH}, "options"),
    Output({"type": "sampler-dropdown", "id": MATCH}, "value"),
    Input({"type": "add-custom-button", "id": MATCH}, "n_clicks"),
    State({"type": "custom-input", "id": MATCH}, "value"),
    State({"type": "sampler-dropdown", "id": MATCH}, "options"),
    State({"type": "sampler-dropdown", "id": MATCH}, "value"),
    prevent_initial_call=True
)
def add_custom_value(n_clicks, custom_value, current_options, current_value):
    if custom_value is not None:
        new_option = {"label": str(custom_value), "value": custom_value}
        if new_option not in current_options:
            current_options.append(new_option)
            current_value = current_value + [custom_value] if current_value else [custom_value]
    return current_options, current_value

@app.callback(
    Output({"type": "sampler-temp-dropdown", "index": MATCH}, "options"),
    Output({"type": "sampler-temp-dropdown", "index": MATCH}, "value"),
    Input({"type": "add-custom-temp", "index": MATCH}, "n_clicks"),
    State({"type": "custom-temp-input", "index": MATCH}, "value"),
    State({"type": "sampler-temp-dropdown", "index": MATCH}, "options"),
    State({"type": "sampler-temp-dropdown", "index": MATCH}, "value"),
    prevent_initial_call=True
)
def add_custom_temperature(n_clicks, custom_temp, current_options, current_value):
    if custom_temp is not None:
        new_option = {"label": str(custom_temp), "value": custom_temp}
        if new_option not in current_options:
            current_options.append(new_option)
            current_value = current_value + [custom_temp] if current_value else [custom_temp]
    return current_options, current_value

# updating based on selections and inputs
@app.callback(
    Output({"type": "discrete-container", "param": MATCH}, "style"),
    Output({"type": "continuous-container", "param": MATCH}, "style"),
    Input({"type": "toggle", "param": MATCH}, "value")
)
def toggle_input_type(is_continuous):
    if is_continuous:
        return {"display": "none"}, {"display": "block"}
    else:
        return {"display": "block"}, {"display": "none"}
    
@app.callback(
    Output("sampler-polymer-image-preview", "children"),
    Input("sampler-polymer-image", "contents"),
    State("sampler-polymer-image", "filename"),
    prevent_initial_call=True
)
def update_image_preview(contents, filename):
    if contents is None:
        return []
    
    return html.Div([
        html.Img(src=contents, style={'maxHeight': '200px', 'maxWidth': '100%'}),
        html.P(filename)
    ])

@app.callback(
    Output("temperature-container", "style"),
    Output("sampler-temperature-options", "children"),
    Input("sampler-solvent-dropdown", "value")
)
def update_temperature_options(selected_solvents):
    if not selected_solvents:
        return {'display': 'none'}, []
    
    temp_options = []
    for solvent in selected_solvents:
        temp_options.append(
            html.Div([
                dbc.Row(
                    [
                        dbc.Col([html.H6(f"Temperature for {solvent}:")], width=8),
                        dbc.Col(
                            [
                                dbc.Switch(
                                    id={"type": "toggle", "param": f"temp-{solvent}"},
                                    label="Continuous",
                                    value=False,
                                ),
                            ],
                            width=2,
                        ),
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
                                            id={"type": "sampler-temp-dropdown", "index": solvent},
                                            options=[{"label": str(temp), "value": temp} for temp in TEMP_CHOICES_D[solvent]],
                                            multi=True,
                                            value=TEMP_CHOICES_D[solvent],
                                        ),
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    dbc.InputGroup([
                                        dbc.Input(id={"type": "custom-temp-input", "index": solvent}, type="number", placeholder="Custom temperature"),
                                        dbc.Button("Add", id={"type": "add-custom-temp", "index": solvent}, size="sm"),
                                    ]),
                                    width=4,
                                )
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "discrete-container", "param": f"temp-{solvent}"},
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.InputGroup(
                                            [
                                                dbc.Input(id={"type": "temp-min", "index": solvent}, type="number", placeholder="Min", value=TEMP_CHOICES_C[solvent][0]),
                                                dbc.Input(id={"type": "temp-max", "index": solvent}, type="number", placeholder="Max", value=TEMP_CHOICES_C[solvent][1]),
                                            ]
                                        ),
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    id={"type": "continuous-container", "param": f"temp-{solvent}"},
                    style={"display": "none"},
                ),
            ])
        )
    
    return {'display': 'block'}, temp_options

@app.callback(
    Output("sampler-results-table", "children"),
    Output("sampler-alert", "children"),
    Output("sampler-alert", "is_open"),
    Output("sampler-alert", "color"),
    Output("sampler-save-button", "disabled"),
    Input("sampler-generate-button", "n_clicks"),
    [
        State("sampler-campaign-name", "value"),
        State("sampler-polymer-name", "value"),
        State("sampler-smiles-string", "value"),
        State("sampler-mw", "value"),
        State("sampler-pdi", "value"),
        State("sampler-solvent-dropdown", "value"),
        State({"type": "toggle", "param": ALL}, "value"),
        State({"type": "toggle", "param": ALL}, "id"),
        State({"type": "sampler-temp-dropdown", "index": ALL}, "value"),
        State({"type": "sampler-temp-dropdown", "index": ALL}, "id"),
        State({"type": "temp-min", "index": ALL}, "value"),
        State({"type": "temp-min", "index": ALL}, "id"),
        State({"type": "temp-max", "index": ALL}, "value"),
        State({"type": "temp-max", "index": ALL}, "id"),
        State({"type": "sampler-dropdown", "id": "concentration"}, "value"),
        State({"type": "toggle", "param": "concentration"}, "value"),
        State("concentration-min", "value"),
        State("concentration-max", "value"),
        State({"type": "sampler-dropdown", "id": "printing-gap"}, "value"),
        State({"type": "toggle", "param": "printing-gap"}, "value"),
        State("printing-gap-min", "value"),
        State("printing-gap-max", "value"),
        State({"type": "sampler-dropdown", "id": "precursor-volume"}, "value"),
        State({"type": "toggle", "param": "precursor-volume"}, "value"),
        State("precursor-volume-min", "value"),
        State("precursor-volume-max", "value"),
        State({"type": "sampler-dropdown", "id": "motor-speed"}, "value"),
        State({"type": "toggle", "param": "motor-speed"}, "value"),
        State("motor-speed-min", "value"),
        State("motor-speed-max", "value"),
        State("sampler-method-dropdown", "value"),
        State("sampler-num-samples", "value"),
    ],
    prevent_initial_call=True,
)
def generate_parameter_sets(n_clicks, campaign_name, polymer_name, smiles_string, mw, pdi, 
                            solvents, toggle_values, toggle_ids, temp_dropdown_values, 
                            temp_dropdown_ids, temp_min_values, temp_min_ids, 
                            temp_max_values, temp_max_ids, concentration_range, 
                            concentration_toggle, concentration_min, concentration_max, 
                            printing_gaps, printing_gap_toggle, printing_gap_min, 
                            printing_gap_max, precursor_vol, precursor_vol_toggle, 
                            precursor_vol_min, precursor_vol_max, motor_speeds, 
                            motor_speed_toggle, motor_speed_min, motor_speed_max, 
                            sampling_method, num_samples):
    if not solvents:
        return None, "Please select at least one solvent.", True, "danger", True
    
    try:
        temp_toggles = {}
        temp_discrete_values = {}
        temp_min = {}
        temp_max = {}
        
        for toggle_value, toggle_id in zip(toggle_values, toggle_ids):
            param = toggle_id["param"]
            if param.startswith("temp-"):
                solvent = param.replace("temp-", "")
                temp_toggles[solvent] = toggle_value
        
        for dropdown_value, dropdown_id in zip(temp_dropdown_values, temp_dropdown_ids):
            solvent = dropdown_id["index"]
            temp_discrete_values[solvent] = dropdown_value
        
        for min_value, min_id in zip(temp_min_values, temp_min_ids):
            solvent = min_id["index"]
            temp_min[solvent] = min_value
        
        for max_value, max_id in zip(temp_max_values, temp_max_ids):
            solvent = max_id["index"]
            temp_max[solvent] = max_value

        parameter_sets = []
        sample_count = 1
        
        for solvent in solvents:
            is_temp_continuous = temp_toggles.get(solvent, False)
            
            for _ in range(num_samples):
                if is_temp_continuous:
                    min_temp = temp_min.get(solvent, TEMP_CHOICES_C[solvent][0])
                    max_temp = temp_max.get(solvent, TEMP_CHOICES_C[solvent][1])
                    temperature = round(random.uniform(min_temp, max_temp))
                else:
                    temp_options = temp_discrete_values.get(solvent, TEMP_CHOICES_D[solvent])
                    temperature = round(random.choice(temp_options))

                if concentration_toggle:
                    concentration = round(random.uniform(concentration_min, concentration_max), 2)
                else:
                    concentration = random.choice(concentration_range) if concentration_range else random.choice(CONCEN_D)

                if printing_gap_toggle:
                    printing_gap = round(random.uniform(printing_gap_min, printing_gap_max))
                else:
                    printing_gap = random.choice(printing_gaps) if printing_gaps else random.choice(PRINT_GAP_D)
                
                if precursor_vol_toggle:
                    precursor_volume = round(random.uniform(precursor_vol_min, precursor_vol_max), 1)
                else:
                    precursor_volume = random.choice(precursor_vol) if precursor_vol else random.choice(PREC_VOL_D)

                if motor_speed_toggle:
                    log_speed_min = math.log10(motor_speed_min)
                    log_speed_max = math.log10(motor_speed_max)
                    log_speed = log_speed_min + random.random() * (log_speed_max - log_speed_min)
                    motor_speed = round(10 ** log_speed, 2)
                else:
                    motor_speed = random.choice(motor_speeds) if motor_speeds else random.choice(MOTOR_SPEEDS_D)
                
                # make all the parameters normalized between 0 and 1 using min-max normalization
                if motor_speed_toggle:
                    log_speed_min = math.log10(motor_speed_min)
                    log_speed_max = math.log10(motor_speed_max)
                    motor_speed_norm = (math.log10(motor_speed) - log_speed_min) / (log_speed_max - log_speed_min) if log_speed_max - log_speed_min != 0 else 0
                else:
                    motor_speeds_list = motor_speeds if motor_speeds else MOTOR_SPEEDS_D
                    log_min = math.log10(min(motor_speeds_list))
                    log_max = math.log10(max(motor_speeds_list))
                    motor_speed_norm = (math.log10(motor_speed) - log_min) / (log_max - log_min) if log_max - log_min != 0 else 0

                if is_temp_continuous:
                    min_temp = temp_min.get(solvent, TEMP_CHOICES_C[solvent][0])
                    max_temp = temp_max.get(solvent, TEMP_CHOICES_C[solvent][1])
                    temperature_norm = (temperature - min_temp) / (max_temp - min_temp)
                else:
                    temp_options = temp_discrete_values.get(solvent, TEMP_CHOICES_D[solvent])
                    temperature_norm = (temperature - min(temp_options)) / (max(temp_options) - min(temp_options))

                if concentration_toggle:
                    concentration_norm = (concentration - concentration_min) / (concentration_max - concentration_min) if concentration_max - concentration_min != 0 else 0
                else:
                    concentration_list = concentration_range if concentration_range else CONCEN_D
                    concentration_norm = (concentration - min(concentration_list)) / (max(concentration_list) - min(concentration_list)) if max(concentration_list) - min(concentration_list) != 0 else 0

                if printing_gap_toggle:
                    printing_gap_norm = (printing_gap - printing_gap_min) / (printing_gap_max - printing_gap_min) if printing_gap_max - printing_gap_min != 0 else 0
                else:
                    printing_gaps_list = printing_gaps if printing_gaps else PRINT_GAP_D
                    printing_gap_norm = (printing_gap - min(printing_gaps_list)) / (max(printing_gaps_list) - min(printing_gaps_list)) if max(printing_gaps_list) - min(printing_gaps_list) != 0 else 0

                if precursor_vol_toggle:
                    precursor_volume_norm = (precursor_volume - precursor_vol_min) / (precursor_vol_max - precursor_vol_min) if precursor_vol_max - precursor_vol_min != 0 else 0
                else:
                    precursor_vol_list = precursor_vol if precursor_vol else PREC_VOL_D
                    precursor_volume_norm = (precursor_volume - min(precursor_vol_list)) / (max(precursor_vol_list) - min(precursor_vol_list)) if max(precursor_vol_list) - min(precursor_vol_list) != 0 else 0

                parameter_set = {
                    "sample_no": sample_count,
                    "campaign_name": campaign_name,
                    "polymer_name": polymer_name,
                    "smiles_string": smiles_string,
                    "mw": mw,
                    "pdi": pdi,
                    "motor_speed": motor_speed,
                    "temperature": temperature,
                    "concentration": concentration,
                    "printing_gap": printing_gap,
                    "precursor_volume": precursor_volume,
                    "solvent": solvent,
                    "motor_speed_norm": motor_speed_norm,
                    "temperature_norm": temperature_norm,
                    "concentration_norm": concentration_norm,
                    "printing_gap_norm": printing_gap_norm,
                    "precursor_volume_norm": precursor_volume_norm
                }
                
                parameter_sets.append(parameter_set)
                sample_count += 1
        
        df = pd.DataFrame(parameter_sets)

        table = dash_table.DataTable(
            id="sampler-results",
            columns=[
                {"name": "Sample No", "id": "sample_no"},
                {"name": "Motor Speed", "id": "motor_speed"},
                {"name": "Temperature", "id": "temperature"},
                {"name": "Concentration", "id": "concentration"},
                {"name": "Printing Gap", "id": "printing_gap"},
                {"name": "Precursor Volume", "id": "precursor_volume"},
                {"name": "Solvent", "id": "solvent"},
            ],
            data=parameter_sets,
            style_table={"overflowX": "auto"},
        )

        if len(df) >= 2:
            X = df[['motor_speed_norm', 'temperature_norm', 'concentration_norm', 
                'printing_gap_norm', 'precursor_volume_norm']].values
            
            pca = PCA(n_components=2)
            pca_result = pca.fit_transform(X)
            
            reducer = umap.UMAP(random_state=42, n_neighbors=min(5, len(df)-1))
            umap_result = reducer.fit_transform(X)
            
            n_background = 1000
            background_points = np.random.rand(n_background, X.shape[1])
            
            background_pca = pca.transform(background_points)
            background_umap = reducer.transform(background_points)
            
            pca_fig = go.Figure()
            
            x_min, x_max = background_pca[:,0].min(), background_pca[:,0].max()
            y_min, y_max = background_pca[:,1].min(), background_pca[:,1].max()
            
            xi = np.linspace(x_min, x_max, 100)
            yi = np.linspace(y_min, y_max, 100)
            xi, yi = np.meshgrid(xi, yi)
            
            positions = np.vstack([xi.ravel(), yi.ravel()])
            values = np.vstack([background_pca[:,0], background_pca[:,1]])
            kernel = gaussian_kde(values)
            z = np.reshape(kernel(positions).T, xi.shape)
            
            pca_fig.add_trace(go.Contour(
                z=z,
                x=xi[0],
                y=yi[:,0],
                colorscale='Blues',
                showscale=False,
                opacity=0.5,
                name='Parameter Space Density'
            ))
            
            for solvent in df['solvent'].unique():
                mask = df['solvent'] == solvent
                pca_fig.add_trace(go.Scatter(
                    x=pca_result[mask, 0],
                    y=pca_result[mask, 1],
                    mode='markers',
                    marker=dict(size=8),
                    name=solvent
                ))
            
            pca_fig.update_layout(
                title='PCA Visualization of Parameter Sets',
                xaxis_title='PCA Component 1',
                yaxis_title='PCA Component 2'
            )
            
            umap_fig = go.Figure()
            
            x_min, x_max = background_umap[:,0].min(), background_umap[:,0].max()
            y_min, y_max = background_umap[:,1].min(), background_umap[:,1].max()
            
            xi = np.linspace(x_min, x_max, 100)
            yi = np.linspace(y_min, y_max, 100)
            xi, yi = np.meshgrid(xi, yi)
            
            positions = np.vstack([xi.ravel(), yi.ravel()])
            values = np.vstack([background_umap[:,0], background_umap[:,1]])
            kernel = gaussian_kde(values)
            z = np.reshape(kernel(positions).T, xi.shape)
            
            umap_fig.add_trace(go.Contour(
                z=z,
                x=xi[0],
                y=yi[:,0],
                colorscale='Blues',
                showscale=False,
                opacity=0.5,
                name='Parameter Space Density'
            ))
            
            for solvent in df['solvent'].unique():
                mask = df['solvent'] == solvent
                umap_fig.add_trace(go.Scatter(
                    x=umap_result[mask, 0],
                    y=umap_result[mask, 1],
                    mode='markers',
                    marker=dict(size=8),
                    name=solvent
                ))
            
            umap_fig.update_layout(
                title='UMAP Visualization of Parameter Sets',
                xaxis_title='UMAP Component 1',
                yaxis_title='UMAP Component 2'
            )

            res = html.Div([
                html.Div([
                    html.Div([
                        dcc.Graph(figure=pca_fig)
                    ], className="col-md-6"),
                    html.Div([
                        dcc.Graph(figure=umap_fig)
                    ], className="col-md-6"),
                ], className="row"),
                table
            ])
        else:
            res = html.Div([
                html.P("Not enough data points for visualization. Generate more samples."),
                html.H3("Generated Parameter Sets"),
                table
            ])

        
        return res, f"Generated {len(parameter_sets)} parameter sets using simple random sampling.", True, "success", False
    except Exception as e:
        print(f"Error generating parameter sets: {e}")
        return None, f"Failed to generate parameter sets: {str(e)}", True, "danger", True



if __name__ == "__main__":
    app.run(debug=True)


# @app.callback(
#     Output("data-output-div", "children"),
#     Input("load-data-button", "n_clicks"),
#     prevent_initial_call=True,
# )
# def load_data(n):
#     print('load_data')
#     # val = ""
#     # docs = mongo.db["recipes"].find()
#     # for doc in docs:
#     #     val += str(doc)
#     #     val += "<br><br>"
#     # nval = val.
#     return (json.dumps(str(com.document)))


# class DashLoggerHandler(logging.StreamHandler):
#     def __init__(self):
#         logging.StreamHandler.__init__(self)
#         self.queue = []

#     def emit(self, record):
#         msg = self.format(record)
#         self.queue.append(msg)


# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
# dashLoggerHandler = DashLoggerHandler()
# logger.addHandler(dashLoggerHandler)

# logger = logging.getLogger(invoker.log.name)
# logger.setLevel(logging.DEBUG)
# from io import StringIO
# log_capture = StringIO()

# # Create a stream handler and set its stream to the log_capture object
# stream_handler = logging.StreamHandler(log_capture)
# logger.addHandler(stream_handler)
# log_messages = []

# import sys
# from io import StringIO
# stringio = StringIO()
# sys.stdout = stringio
# @app.callback(Output('console-output', 'value'), [Input('update-interval', 'n_intervals')])
# def show_console_output(n):
#     # Retrieve console output from StringIO object
#     stringio.seek(0)
#     console_output = stringio.read()
#     return console_output

# @app.callback(Output("page-content", "children"), [Input("url", "pathname")])
# def display_page(pathname):
#     print("\n\nrefreshing to " + pathname)
#     if pathname == "/":
#         return home_layout
#     elif pathname == "/edit-recipe":
#         return edit_recipe_layout
#     elif pathname == "/execute-recipe":
#         return execute_recipe_layout
#     elif pathname == "/data":
#         return data_layout
#     else:
#         return html.Div("404")


# data_list4 = com.device_list

# dl5 = []
# for list in data_list4:
#     dl5.append(list.__dict__)

# print(dl5[2]['motor'].__dict__)


# @app.callback(
#         Output("commands-accordion", "children"),
#         Input("add-command-button", "n_clicks"),
#         State("commands-accordion", "children"),
#         prevent_initial_call=True,
#         allow_duplicate=True
# )
# def add_command_accordian(n_clicks, children):
#     children=[
#         dbc.AccordionItem(
#             "new item", title="new title", item_id="new")
#     ]

#     return children


# @app.callback(
#     Output("commands-accordion", "children"),
#     Input("refresh-button2", "n_clicks"),
#     State("commands-accordion", "children"),
#     # allow_duplicate=True
# )
# def load_commands_accordion(n_clicks, children):
#     children = []
#     # print()
#     command_list = com.get_unlooped_command_list().copy()
#     # print(command_list)
#     # for command in command_list:
#     #     if isinstance(command, CompositeCommand):
#     #         for sub_command in command._command_list:
#     #             sub_command._receiver = sub_command._receiver._name
#     #             sub_command = sub_command.__dict__
#     #     else:
#     #         # print(command.__dict__)
#     #         command._receiver = command._receiver._name
#     command_params = []
#     for command in command_list:
#         # if isinstance(command, CompositeCommand):
#         # print(type(command).__name__)
#         temp_dict_command_params = {"command": type(command).__name__}
#         temp_dict_command_params.update({"params": command.get_init_args()})
#         command_params.append(temp_dict_command_params)
#         # print(command._params)
#         # else:
#         #     command_params.append(command._params)
#     # print(command_params)
#     # print(com.get_command_names())
#     for index, command in enumerate(command_params):
#         # print(command)
#         children.append(
#             dbc.AccordionItem(
#                 dcc.Markdown(
#                     children=[
#                         "**Command Object:**",
#                         "```json",
#                         json.dumps(command, indent=4, cls=util.Encoder),
#                         # str(command.__dict__),
#                         "```",
#                     ],
#                 ),
#                 # str(command.__dict__),
#                 title=command["command"],
#                 item_id=command["command"] + str(index),
#             )
#         )
#     return children


# @app.callback(
#     Output("table-container3", "children"),
#     [Input("refresh-button3", "n_clicks")],
#     [State("table-container3", "children")],
# )
# def update_table3(n_clicks, table):
#     table_data3 = data_list3
#     table = dash_table.DataTable(
#         data=table_data3,
#         columns=[{"name": "Name", "id": "Name"}, {"name": "Value", "id": "Value"}],
#     )
#     return table
