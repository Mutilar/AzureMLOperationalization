import azure.functions as func
from yaml import safe_load as load
from base64 import b64encode as encode
from time import sleep
import sys
import os
sys.path.append("handlers")

raise Exception(os.listdir())

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
    """ Decodes ServiceBus message trigger and delegates to helper functions to handle
    two unique job cases: kick-off and wrap-up.
    """

    # Converts bytes into JSON
    params = load(
        msg.get_body().decode("utf-8")
    )

    # Kicks off test runs to Azure ML Compute, called from a CI pipeline
    if params["job"] == START_BUILD:
        start_build_pipeline(params)

    # Updates telemetry in Azure DevOps, called from a Experiment Run
    elif params["job"] == UPDATE_BUILD:
        update_build_pipeline(params)


def start_build_pipeline(params):
    """ Fetches the repository of interest, creates a new Experiment SDK Object,
    and submits a set of notebook Runs to that object after injecting try-catch statements
    to facilitate callbacks to the DevOps pipeline.
    """

    # Relevant parameter groups
    az_params = params["azure_resources"]
    cb_params = params["wrap_up"]["call_back"]
    rc_params = params["run_config"]
    sp_params = az_params["service_principal"]
    ws_params = az_params["workspace"]

    # Notebooks passed in as a comma seperated list
    changed_notebooks = rc_params["notebooks"].split(",")

    # Downloads repo to staging folder
    fh.prepare_staging(
        repo=dh.get_repository(
            project_url=cb_params["project_url"],
            root=rc_params["root"],
            version=rc_params["version"],
            auth_token=params["auth_token"]
        ),
        root=rc_params["root"]
    )

    # Fetches Experiment to submit runs on
    exp = ah.fetch_exp(
        sp_username=sp_params["username"],
        sp_tenant=sp_params["tenant"],
        sp_password=sp_params["password"],
        ws_name=ws_params["name"],
        ws_subscription_id=ws_params["subscription_id"],
        ws_resource_group=ws_params["resource_group"],
        build_id=params["build_id"]
    )

    # Submits notebook runs to Experiment, delimiting by commas
    for notebook in changed_notebooks:

        # Creates new DevOps Test Run
        response = dh.post_new_run(
            notebook=notebook,
            project_url=cb_params["project_url"],
            project=az_params["project"],
            build_id=params["build_id"],
            auth_token=params["auth_token"]
        )
        devops_run_id = response.json()["id"]

        # Collects required pip packages and associated files
        rq_params = fh.fetch_requirements(notebook)

        # Moves necessary files into snapshot directory
        fh.build_snapshot(
            notebook=notebook,
            dependencies=rq_params["dependencies"],
            requirements=rq_params["requirements"],
            postexec=rq_params["postexec"],
            conda_file=rc_params["conda_file"],
            ws_name=ws_params["name"],
            ws_subscription_id=ws_params["subscription_id"],
            ws_resource_group=ws_params["resource_group"]
        )

        # Adds try-catch callback mechanism to notebook
        fh.add_notebook_callback(
            notebook=notebook,
            params=params,
            devops_run_id=devops_run_id,
            postexec=rq_params["postexec"],
            preexec=rq_params["preexec"]
        )

        # Submits notebook Run to Experiment
        run = ah.submit_run(
            notebook=notebook,
            exp=exp,
            timeout=rq_params["celltimeout"],
            compute_target=rc_params["compute_target"],
            base_image=rc_params["base_image"],
            sp_username=sp_params["username"],
            sp_tenant=sp_params["tenant"],
            sp_password=sp_params["password"]
        )
        
        # Marks Run with relevant properties
        run.tag("file", notebook)
        run.tag("devops_run_id", devops_run_id)


def update_build_pipeline(params):
    """ Updates the DevOps Test Runs based on results from Azure ML Compute, 
    and checks to close the pipeline if all Runs are completed.
    """

    cb_params = params["wrap_up"]["call_back"]
    az_params = params["azure_resources"]
    sp_params = az_params["service_principal"]
    ws_params = az_params["workspace"]

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

    # Checks if all Runs have finished, and if any have failed
    exp_status = ah.fetch_exp_status(exp)

    # Closes pipeline if all Runs are finished
    if exp_status["finished"] is True:
        result = FAILED_PIPELINE if (exp_status["failed"] is True and params["run_condition"] == ALL_NOTEBOOKS_MUST_PASS) else PASSED_PIPELINE
        dh.post_pipeline_callback(
            result=result,
            project_url=cb_params["project_url"],
            project_id=cb_params["project_id"],
            hub_name=cb_params["hub_name"],
            plan_id=cb_params["plan_id"],
            task_id=cb_params["task_id"],
            job_id=cb_params["job_id"],
            auth_token=params["auth_token"]
        )


    # Allows for finalization of current Run
    retries = 3
    while retries > 0:
        try:
            # Gets current Run
            run = ah.fetch_run(
                exp=exp,
                devops_run_id=az_params["devops_run_id"]
            )

            # Scrubs and attachments output notebook
            run.download_file(
                name="outputs/output.ipynb",
                output_file_path="snapshot/outputs/output.ipynb"
            )
            output_notebook_string = fh.remove_notebook_callback("snapshot/outputs/output.ipynb")
            output_notebook_stream = encode(output_notebook_string.encode("utf-8"))
            dh.post_run_attachment(
                file_name="output.ipynb",
                stream=output_notebook_stream,
                project_url=cb_params["project_url"],
                project=az_params["project"],
                devops_run_id=az_params["devops_run_id"],
                auth_token=params["auth_token"]
            )
            dh.post_run_attachment(
                file_name="output.txt",
                stream=output_notebook_stream,
                project_url=cb_params["project_url"],
                project=az_params["project"],
                devops_run_id=az_params["devops_run_id"],
                auth_token=params["auth_token"]
            )

            # Attaches Run's output logs
            logs = run.get_all_logs("snapshot/outputs/")
            for log in logs:
                dh.post_run_attachment(
                    file_name=os.path.basename(log),
                    stream=encode(fh.get_file_str(log).encode("utf-8")),
                    project_url=cb_params["project_url"],
                    project=az_params["project"],
                    devops_run_id=az_params["devops_run_id"],
                    auth_token=params["auth_token"]
                )
            dh.post_run_results(
                error_message=cb_params["error_message"],
                run_details=run.get_details(),
                project_url=cb_params["project_url"],
                project=az_params["project"],
                devops_run_id=az_params["devops_run_id"], 
                auth_token=params["auth_token"]
            )
            dh.patch_run_update(
                error_message=cb_params["error_message"],
                project_url=cb_params["project_url"],
                project=az_params["project"],
                devops_run_id=az_params["devops_run_id"], 
                auth_token=params["auth_token"]
            )
            retries = 0
        except Exception as e:
            retries -= 1
            sleep(60)
