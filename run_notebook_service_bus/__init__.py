import azure.functions as func
from yaml import safe_load as load
from base64 import b64encode as encode
from time import sleep
import sys
import os
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

    rc_params = params["run_config"]
    az_params = params["azure_resources"]
    sp_params = az_params["service_principal"]
    ws_params = az_params["workspace"]

    changed_notebooks = rc_params["notebooks"].split(",")

    # To be supplied by the "get changed notebooks" script
    # changed_notebooks = [
        # "notebooks/how-to-use-azureml/automated-machine-learning/classification/auto-ml-classification.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/regression/auto-ml-regression.ipynb", # NO MODULE NAMED CHECKCELLOUTPUT
        # "notebooks/how-to-use-azureml/automated-machine-learning/remote-amlcompute/auto-ml-remote-amlcompute.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/remote-amlcompute-with-onnx/auto-ml-remote-amlcompute-with-onnx.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/missing-data-blacklist-early-termination/auto-ml-missing-data-blacklist-early-termination.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/sparse-data-train-test-split/auto-ml-sparse-data-train-test-split.ipynb", # MODULE PANDAS COMPAT HAS NO ATTRIBUTE ITERITEMS
        # "notebooks/how-to-use-azureml/automated-machine-learning/exploring-previous-runs/auto-ml-exploring-previous-runs.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/classification-with-deployment/auto-ml-classification-with-deployment.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/sample-weight/auto-ml-sample-weight.ipynb", # WEIRD POSTEXEC ERROR
        # "notebooks/how-to-use-azureml/automated-machine-learning/subsampling/auto-ml-subsampling-local.ipynb", # RUN SUCCESSFULLY
        # "notebooks/how-to-use-azureml/automated-machine-learning/dataprep/auto-ml-dataprep.ipynb", # MODULE PANDAS COMPAT HAS NO ATTRIBUTE ITERITEMS
        # "notebooks/how-to-use-azureml/automated-machine-learning/dataprep-remote-execution/auto-ml-dataprep-remote-execution.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/model-explanation/auto-ml-model-explanation.ipynb", # RUN SUCCESSFULLY
        # "notebooks/how-to-use-azureml/automated-machine-learning/classification-with-whitelisting/auto-ml-classification-with-whitelisting.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/forecasting-energy-demand/auto-ml-forecasting-energy-demand.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/forecasting-orange-juice-sales/auto-ml-forecasting-orange-juice-sales.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/forecasting-bike-share/auto-ml-forecasting-bike-share.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/classification-with-onnx/auto-ml-classification-with-onnx.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/classification-credit-card-fraud/auto-ml-classification-credit-card-fraud.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/classification-bank-marketing/auto-ml-classification-bank-marketing.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/regression-hardware-performance/auto-ml-regression-hardware-performance.ipynb",
        # "notebooks/how-to-use-azureml/automated-machine-learning/regression-concrete-strength/auto-ml-regression-concrete-strength.ipynb" # COULD NOT FIND MODEL WITH VALID SCORE FOR METRIC SPEARMAN CORRELATION
    # ]

    # Downloads repo to staging folder
    fh.fetch_repo(
        repo=rc_params["repo"],
        version=rc_params["version"]
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
            organization=az_params["organization"],
            project=az_params["project"],
            build_id=params["build_id"],
            auth_token=params["auth_token"]
        )
        run_id = response.json()["id"]

        # Collects required pip packages and associated files
        rq_params = fh.fetch_requirements(notebook)

        # Moves necessary files into snapshot directory
        fh.build_snapshot(
            notebook=notebook,
            dependencies=rq_params["dependencies"],
            requirements=rq_params["requirements"] + ["azure-servicebus", "azureml", "azureml-sdk"],
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
            run_id=run_id,
            postexec=rq_params["postexec"],
            preexec=rq_params["preexec"]
        )

        # Submits notebook Run to Experiment
        run = ah.submit_run(
            notebook=notebook,
            exp=exp,
            timeout=rq_params["celltimeout"],
            conda_file=rc_params["conda_file"],
            compute_target=rc_params["compute_target"],
            base_image=rc_params["base_image"]
        )
        
        # Marks Run with relevant properties
        run.tag("file", notebook)
        run.tag("run_id", run_id)


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
            organization=az_params["organization"],
            project_id=cb_params["project_id"],
            hub_name=cb_params["hub_name"],
            plan_id=cb_params["plan_id"],
            task_id=cb_params["task_id"],
            job_id=cb_params["job_id"],
            auth_token=params["auth_token"]
        )

    # Allows for finalization of current Run
    sleep(45) 

    # Gets current Run
    run = ah.fetch_run(
        exp=exp,
        run_id=az_params["run_id"]
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

    # Attaches Run's output logs
    logs = run.get_all_logs("snapshot/outputs/")
    for log in logs:
        r = dh.post_run_attachment(
            file_name=log.split("/")[-1],
            stream=encode(fh.get_file_str(log).encode("utf-8")),
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
