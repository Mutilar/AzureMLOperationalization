import azure.functions as func
from yaml import safe_load as load
from base64 import b64encode as encode
from time import sleep
import sys
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

# Directories
OUTPUT_NOTEBOOK_LOCATION = "snapshot/outputs/output.ipynb"

def main(msg: func.ServiceBusMessage):

    # Converts bytes into JSON
    # https://docs.microsoft.com/en-us/python/api/azure-functions/azure.functions.servicebusmessage?view=azure-python

    params = load(
        msg.get_body().decode("utf-8")
    )

    raise Exception(str(msg.user_properties) + "\n" str(params))

    # Kicks off test runs to Azure ML Compute, called from a CI pipeline
    if params["job"] == START_BUILD:
        start_build_pipeline(params)
    
    # # Updates telemetry in Azure DevOps, called from a Experiment Run
    elif params["job"] == UPDATE_BUILD:
        update_build_pipeline(params)


def start_build_pipeline(params):
    rc_params = params["run_config"]
    az_params = params["azure_resources"]
    sp_params = az_params["service_principal"]
    ws_params = az_params["workspace"]

    # Downloads repo to snapshot folder and adds SB pip dependency for callback
    fh.fetch_repo(
        repo=rc_params["repo"],
        version=rc_params["version"]
    )
    fh.add_pip_dependency(
        conda_file=rc_params["conda_file"],
        dependency="azure-servicebus"
    )

    # Fetches Experiment to submit Runs on
    exp = ah.fetch_exp(
        sp_username=sp_params["username"],
        sp_tenant=sp_params["tenant"],
        sp_password=sp_params["password"],
        ws_name=ws_params["name"],
        ws_subscription_id=ws_params["subscription_id"],
        ws_resource_group=ws_params["resource_group"],
        build_id=params["build_id"]
    )

    for notebook in rc_params["notebooks"].split(","):

        # Creates new DevOps Test Run
        response = dh.post_new_run(
            notebook=notebook,
            organization=az_params["organization"],
            project=az_params["project"],
            build_id=params["build_id"],
            auth_token=params["auth_token"]
        )
        run_id = response.json()["id"]

        # Adds try-catch callback mechanism to notebook
        fh.add_notebook_callback(
            notebook=notebook, 
            params=params, 
            run_id=run_id
        )

        # Submits notebook Run to Experiment
        run = ah.submit_run(
            notebook=notebook,
            exp=exp,
            conda_file=rc_params["conda_file"],
            compute_target=rc_params["compute_target"],
            base_image=rc_params["base_image"]
        )

        # Marks Run with relevant properties
        run.tag("file",notebook)
        run.tag("run_id", run_id)


def update_build_pipeline(params):
    cb_params = params["wrap_up"]["call_back"]
    az_params = params["azure_resources"]
    sp_params = az_params["service_principal"]
    ws_params = az_params["workspace"]
    
    # Allows for finalization of current Run
    sleep(120) 

    # Fetches Experiment to fetch Runs from
    exp = ah.fetch_exp(
        sp_username=sp_params["username"],
        sp_tenant=sp_params["tenant"],
        sp_password=sp_params["password"],
        ws_name=ws_params["name"],
        ws_subscription_id=ws_params["subscription_id"],
        ws_resource_group=ws_params["resource_group"],
        build_id=params["build_id"]
    )

    # Gets current Run
    run = ah.fetch_run(
        exp=exp,
        run_id=az_params["run_id"]
    )
    
    # Download, scrub, and stream output notebook
    run.download_file(
        name="outputs/output.ipynb",
        output_file_path=OUTPUT_NOTEBOOK_LOCATION
    )
    output_notebook_string = fh.remove_notebook_callback(OUTPUT_NOTEBOOK_LOCATION)
    output_notebook_stream = encode(output_notebook_string.encode("utf-8"))

    # Updates Test Results with Run's telemetry and output notebook
    dh.post_run_attachment(
        file_name="output.ipynb",
        stream=output_notebook_stream,
        organization=az_params["organization"],
        project=az_params["project"],
        run_id=az_params["run_id"],
        auth_token=params["auth_token"]
    )
    dh.post_run_attachment(
        file_name="output.txt",
        stream=output_notebook_stream,
        organization=az_params["organization"],
        project=az_params["project"],
        run_id=az_params["run_id"],
        auth_token=params["auth_token"]
    )
    dh.post_run_results(
        error_message=cb_params["error_message"],
        run_details=run.get_details(),
        organization=az_params["organization"],
        project=az_params["project"],
        run_id=az_params["run_id"], 
        auth_token=params["auth_token"]
    )
    dh.patch_run_update(
        error_message=cb_params["error_message"],
        organization=az_params["organization"],
        project=az_params["project"],
        run_id=az_params["run_id"], 
        auth_token=params["auth_token"]
    )

    # Checks if all Runs have finished, and if any have failed
    exp_status = ah.fetch_exp_status(exp)

    # Closes pipeline if all Runs are finished
    if exp_status["finished"] is True:
        result = FAILED_PIPELINE if (exp_status["failed"] is True and params["run_condition"] == ALL_NOTEBOOKS_MUST_PASS) else PASSED_PIPELINE
        dh.post_pipeline_callback(
            result=result,
            plan_url=cb_params["plan_url"],
            project_id=cb_params["project_id"],
            hub_name=cb_params["hub_name"],
            plan_id=cb_params["plan_id"],
            task_id=cb_params["task_id"],
            job_id=cb_params["job_id"],
            auth_token=params["auth_token"]
        )