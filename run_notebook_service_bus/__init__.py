import azure.functions as func
import yaml
import sys
from time import sleep
sys.path.append("handlers")
import file_handler as fh
import azureml_handler as ah
import devops_handler as dh

# Job types
START_BUILD = "!START"
UPDATE_BUILD = "!UPDATE"

# States of pipelines
PASSED_PIPELINE = "Succeeded"
FAILED_PIPELINE = "Failed"

# Run Conditions for pipelines
ALL_NOTEBOOKS_MUST_PASS = "all_pass"

def main(msg: func.ServiceBusMessage):

    # Converts bytes into JSON
    params = yaml.safe_load(
        msg.get_body().decode("utf-8")
    )

    # Kicks off test runs to Azure ML Compute, called from a CI pipeline
    if params["job"] == START_BUILD:
        start_build_pipeline(params)
    
    # Updates telemetry in Azure DevOps, called from a Experiment Run
    elif params["job"] == UPDATE_BUILD:
        update_build_pipeline(params)


def start_build_pipeline(params):

    # Downloads repo to snapshot folder and adds SB pip dependency for callback
    fh.fetch_repo(
        params["run_config"]["repo"]
    )
    fh.add_pip_dependency(
        params["run_config"]["conda_file"],
        "azure-servicebus"
    )

    # Fetches Experiment to submit Runs on
    exp = ah.fetch_exp(params)

    for notebook in params["run_config"]["notebooks"]:

        # Creates new DevOps Test Run
        response = dh.post_new_run(params, notebook)
        run_id = response.json()["id"]

        # Adds try-catch callback mechanism to notebooks
        fh.add_notebook_callback(params, notebook, run_id)

        # Submits notebook Run to Experiment
        run = ah.submit_run(params, exp, notebook)
        run.tag(notebook)
        run.tag("run_id", run_id)


def update_build_pipeline(params):

    # Allows for finalization of current Run
    sleep(120) 

    # Fetches Experiment to fetch Runs from
    exp = ah.fetch_exp(params)

    # Checks if all Runs have finished, and if any have failed
    exp_status = ah.fetch_exp_status(exp)

    # Gets current Run
    run = ah.fetch_run(
        exp,
        params["azure_resources"]["run_id"]
    )
    
    # Updates Test Results from Run's telemetry
    dh.post_run_results(params, run.get_details())
    dh.patch_run_update(params, run.get_details())

    # Closes pipeline if all Runs are finished
    if exp_status["finished"] is True:
        if exp_status["failed"] is True and params["run_condition"] == ALL_NOTEBOOKS_MUST_PASS:
            dh.post_pipeline_callback(params, FAILED_PIPELINE)
        else:
            dh.post_pipeline_callback(params, PASSED_PIPELINE)