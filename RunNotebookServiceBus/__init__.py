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

    # Called from a YAML build pipeline, kicks off test runs to Azure ML Compute
    if params["job"] == START_BUILD:
        start_build_pipeline(params)


def start_build_pipeline(params):

    # Downloads repository to snapshot folder
    fh.fetch_repository(
        params["run_configuration"]["repository"]
    )

    # Fetches Experiment to submit run on
    exp = ah.fetch_experiment(params)

    # Submits notebook run to Experiment
    for notebook in params["run_configuration"]["notebooks"]:
        run = ah.submit_run(params, exp, notebook)
        run.tag(notebook)
