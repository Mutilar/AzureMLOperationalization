import azure.functions as func

from . import request_handler
from . import file_handler
from . import azureml_handler


# Job types
START_BUILD = "!START"
UPDATE_BUILD = "!UPDATE"

# States of runs
RUN_FAILED = "Failed"
UNFINISHED_RUNS = ["Queued", "Preparing", "Starting", "Running"]

# Pass/fail states for pipelines
PIPELINE_PASSED = "Succeeded"
PIPELINE_FAILED = "Failed"


def start_build_pipeline(params):

    # Downloads repository to snapshot and injects SB dependency
    file_handler.fetch_repository(params["run_configuration"]["repository"])
    file_handler.add_service_bus_dependency(params["run_configuration"]["conda_file"])

    # Fetches Experiment to submit run on
    exp = azureml_handler.fetch_experiment(params)

    # Creates new runs in DevOps, injects code into notebooks, and submits them to the Experiment
    for notebook in params["run_configuration"]["notebooks"]:

        response = request_handler.post_new_run(params, notebook)
        run_id = response.json()["id"]

        file_handler.add_notebook_callback(params, notebook, run_id)

        run = azureml_handler.submit_run(params, exp, notebook)
        run.tag(notebook)


def update_build_pipeline(params):

    exp = azureml_handler.fetch_experiment(params)
    # current_run = handlers.fetch_run(params, exp)

    # Updates Test Results
    request_handler.post_run_results(params, None) # current_run.get_details())

    # Checks if pipeline has finished all runs
    finished_count = 0
    notebook_failed = False
    for run in exp.get_runs():

        if not any(flag in str(run) for flag in UNFINISHED_RUNS):
            finished_count += 1
        
        if RUN_FAILED in str(run):
            notebook_failed = True

    # If all runs are finished, closes pipeline
    if finished_count == len(params["run_configuration"]["notebooks"]):

        if notebook_failed and params["run_condition"] == "all_pass":
            request_handler.post_pipeline_callback(params, PIPELINE_FAILED)
        
        else:
            request_handler.post_pipeline_callback(params, PIPELINE_PASSED)


def main(msg: func.ServiceBusMessage):

    # Converts bytes into JSON and ensures all relevant fields are present
    params = file_handler.parse_and_validate_parameters(msg.get_body().decode("utf-8"))

    if params is None:
        raise Exception ("Parameters not valid")
        return

    # Called from a YAML build definition, kicks off test runs to Azure ML Compute
    if params["job"] == START_BUILD:
        start_build_pipeline(params)

    # Called from a test run, updates telemetry in Azure DevOps and checks to close pipeline
    elif params["job"] == UPDATE_BUILD:
        update_build_pipeline(params)
