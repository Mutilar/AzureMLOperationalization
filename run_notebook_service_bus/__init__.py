import azure.functions as func
import yaml
import sys
sys.path.append("handlers")
import file_handler as fh
import azureml_handler as ah

# Job types
START_BUILD = "!START"


def main(msg: func.ServiceBusMessage):

    # Converts bytes into JSON
    params = yaml.safe_load(
        msg.get_body().decode("utf-8")
    )

    # Kicks off test runs to Azure ML Compute, called from a CI pipeline
    if params["job"] == START_BUILD:
        start_build_pipeline(params)


def start_build_pipeline(params):

    # Downloads repo to snapshot folder
    fh.fetch_repo(
        params["run_config"]["repo"]
    )

    # Fetches Experiment to submit runs on
    exp = ah.fetch_exp(params)

    # Submits notebook runs to Experiment
    for notebook in params["run_config"]["notebooks"]:
        run = ah.submit_run(params, exp, notebook)
        run.tag(notebook)
