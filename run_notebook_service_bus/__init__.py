import azure.functions as func
import yaml
import sys
sys.path.append("handlers")
import file_handler as fh
import azureml_handler as ah

# Job types
START_BUILD = "!START"
UPDATE_BUILD = "!UPDATE"

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
        rc_params["conda_file"],
        'azure-servicebus'
    )

    # Fetches Experiment to submit runs on
    exp = ah.fetch_exp(params)

    for notebook in params["run_config"]["notebooks"]:

        # Creates new DevOps Test
        response = rh.post_new_run(params, notebook)
        run_id = response.json()["id"]

        # Adds try-catch callback mechanism to notebooks
        fh.add_notebook_callback(params, notebook, run_id)

        # Submits notebook Run to Experiment
        run = ah.submit_run(params, exp, notebook)
        run.tag(notebook)


def update_build_pipeline(params):

    # Updates Test Results
    rh.post_run_results(params)