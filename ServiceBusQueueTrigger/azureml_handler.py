from azureml._base_sdk_common.common import perform_interactive_login
from azureml.core import Workspace, Experiment, ScriptRunConfig #, TODO Run?
from azureml.core.conda_dependencies import CondaDependencies
from azureml.core.runconfig import RunConfiguration, DEFAULT_CPU_IMAGE, DEFAULT_GPU_IMAGE
from azureml.contrib.notebook import NotebookRunConfig


def fetch_experiment(params):
    az_params = params["azure_resources"]

    # Getting Service Principal connection
    sp_params = az_params["service_principal"]
    perform_interactive_login(
        username=sp_params["username"],
        tenant=sp_params["tenant"],
        password=sp_params["password"],
        service_principal=True
    )

    # Getting Workspace
    ws_params = az_params["workspace"]
    ws = Workspace.get(
        name=ws_params["name"],
        subscription_id=ws_params["subscription_id"],
        resource_group=ws_params["resource_group"]
    )

    # Getting Experiment from Workspace
    # While Experiment name could be arbitrary, we use it to connect DevOps builds to Experiments in Azure ML Compute for those builds
    exp = Experiment(
        workspace=ws,
        name=params["build_id"]
    )

    # Returning experiment
    return exp


def fetch_run_configuration(rc_params):

    # Init configuration for Python
    run_config = RunConfiguration(framework="python")

    # Specify compute target
    run_config.target = rc_params["compute_target"]

    # Configure Docker parameters
    run_config.environment.docker.enabled = True
    run_config.environment.docker.base_image = DEFAULT_CPU_IMAGE

    # Specify Conda file location
    run_config.environment.python.conda_dependencies = CondaDependencies(
        f'./snapshot/inputs/{rc_params["conda_file"]}'
    )

    # Returning configuration
    return run_config


def submit_run(params, exp, notebook_name):

    # Dispatching job with associated parameters to Azure ML Compute
    run = exp.submit(
        NotebookRunConfig(
            source_directory="snapshot/", # os.path.dirname("snapshot/inputs/" + notebook_name),
            notebook="inputs/" + notebook_name,
            output_notebook="outputs/output.ipynb",
            run_config=fetch_run_configuration(params["run_configuration"]),
        )
    )
    
    # Returning reference to run
    return run
