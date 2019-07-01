# Pythonic helper logic for the function
from .. import helpers

# Triggers, bindings, etc.
import azure.functions as func

# Job types
START_BUILD = "!START"
UPDATE_BUILD = "!UPDATE"

# States of runs
RUN_FAILED = "Failed"
UNFINISHED_RUNS = ["Running", "Queued", "Starting"]

# Pass/fail states for pipelines
PIPELINE_PASSED = "Succeeded"
PIPELINE_FAILED = "Failed"


def start_build_pipeline(params):

    # Downloads repository to snapshot and injects SB dependency
    helpers.fetch_repository(params)
    helpers.add_service_bus_conda_dependency(params)

    # Fetches Experiment to submit run on
    exp = helpers.fetch_experiment(params)

    # Creates new runs in DevOps, injects code into notebooks, and submits them to the Experiment
    for notebook in params["run_configuration"]["notebooks"]:

        response = helpers.post_new_run(params, notebook)
        run_id = response.json()["id"]

        helpers.add_notebook_callback(params, notebook, run_id)

        run = helpers.submit_run(params, exp, notebook)
        run.tag(notebook)


def update_build_pipeline(params):

    exp = helpers.fetch_experiment(params)
    # current_run = helpers.fetch_run(params, exp)

    # Updates Test Results
    helpers.post_run_results(params, None) # current_run.get_details())

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
            helpers.post_pipeline_callback(params, PIPELINE_FAILED)
        else:
            helpers.post_pipeline_callback(params, PIPELINE_PASSED)


def main(msg: func.ServiceBusMessage):

    # Converts byte stream into JSON and ensures all relevant fields are present
    params = helpers.parse_and_validate_parameters(msg)

    if params is None:
        raise Exception ("Parameters not valid")
        return

    # Called from a YAML build definition, kicks off test runs to Azure ML Compute
    if params["job"] == START_BUILD:
        start_build_pipeline(params)

    # Called from a test run, updates telemetry in Azure DevOps and checks to close pipeline
    elif params["job"] == UPDATE_BUILD:
        update_build_pipeline(params)
