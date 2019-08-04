from azureml._base_sdk_common.common import perform_interactive_login
from azureml.core import Workspace, Experiment, ScriptRunConfig, Run
from azureml.core.conda_dependencies import CondaDependencies
from azureml.core.runconfig import RunConfiguration, DEFAULT_CPU_IMAGE, DEFAULT_GPU_IMAGE
from azureml.contrib.notebook import NotebookRunConfig, AzureMLNotebookHandler
import os

# States of runs
FAILED_RUN = "Failed"
UNFINISHED_RUN = ["Queued", "Preparing", "Starting", "Running"]


def fetch_exp(sp_username, sp_tenant, sp_password, ws_name, ws_subscription_id, ws_resource_group, build_id):
    """ Authenticates with the ML Workspace with a Service Principal connection,
    fetches the Workspace, and then fetches and returns a new Experiment.
    """

    # Gets Service Principal connection
    #   AuthenticationException, error: "unauthorized client"
    #       Service Principal credentials are incorrectly set up
    perform_interactive_login(
        username=sp_username,
        tenant=sp_tenant,
        password=sp_password,
        service_principal=True
    )

    # Gets Workspace
    ws = Workspace.get(
        name=ws_name,
        subscription_id=ws_subscription_id,
        resource_group=ws_resource_group
    )

    # Gets Experiment from Workspace
    #   While the Experiment name could be arbitrary, 
    #   we use it to correlate DevOps Builds to their respective Experiments
    exp = Experiment(
        name=build_id,
        workspace=ws
    )

    # Returns experiment
    return exp


def fetch_run_config(conda_file, compute_target, base_image):
    """ Generates a Run Configuration based on the pipeline parameters,
    specifying such things as the Compute Target and Conda Dependencies. 
    """

    # Inits configuration for Python
    run_config = RunConfiguration(framework="python")

    # Specifies compute target
    run_config.target = compute_target

    # Configures Docker parameters
    run_config.environment.docker.enabled = True
    run_config.environment.docker.base_image = base_image

    # Specifies Conda file location
    run_config.environment.python.conda_dependencies = CondaDependencies(
        os.path.join(
            "snapshot/inputs",
            conda_file
        )
    )

    # Returns configuration
    return run_config


def submit_run(notebook, exp, timeout, conda_file, compute_target, base_image, sp_username, sp_tenant, sp_password):
    """ Submits a new Run with configurations based on the pipeline parameters.
    """

    # Dispatches job with associated parameters to Azure ML Compute
    run = exp.submit(
        NotebookRunConfig(
            source_directory="snapshot/",
            notebook=os.path.join(
                "inputs",
                notebook
            ),
            output_notebook="outputs/output.ipynb",
            handler=AzureMLNotebookHandler(
                timeout=timeout,
                cwd=os.path.join(
                    "inputs",
                    os.path.dirname(notebook)
                )
            ),
            params={
                "SP_USERNAME": sp_username,
                "SP_TENANT": sp_tenant,
                "SP_PASSWORD": sp_password
            },
            run_config=fetch_run_config(
                conda_file=conda_file,
                compute_target=compute_target,
                base_image=base_image
            )
        )
    )
    
    # Returns reference to run
    return run

def fetch_run(exp, run_id):
    """ Fetches a Run by its Run ID tag specified by the DevOps Test Run.
    """

    # Finds Run with matching RunID
    for run in exp.get_runs(tags = {
        "run_id": run_id
    }):
        return run
    return None


def fetch_exp_status(exp):
    """ Determines the status of the pipeline by fetching all Runs and checking their status.
    """

    all_finished = True
    any_failed = False
    for run in exp.get_runs():

        # Checks if any Runs are still running
        if any(flag == run.get_status() for flag in UNFINISHED_RUN):
            all_finished = False

        # Checks if any Runs have failed
        if run.get_status() == FAILED_RUN:
            any_failed = True

    return {
        "finished": all_finished,
        "failed": any_failed
    }
