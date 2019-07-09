import azure.functions as func
import sys
sys.path.append("handlers")
import request_handler as rh
import file_handler as fh
import azureml_handler as ah


# Job types
START_BUILD = "!START"
UPDATE_BUILD = "!UPDATE"

# States of runs
RUN_FAILED = "Failed"
UNFINISHED_RUNS = ["Queued", "Preparing", "Starting", "Running"]

# Pass/fail states for pipelines
PIPELINE_PASSED = "Succeeded"
PIPELINE_FAILED = "Failed"


def main(event: func.EventGridEvent):
    # result = json.dumps({
    #     'id': event.id,
    #     'data': event.get_json(),
    #     'topic': event.topic,
    #     'subject': event.subject,
    #     'event_type': event.event_type,
    # })
    # logging.info('Python EventGrid trigger processed an event: %s', result)

    params = event.get_json()

    if params is not None:

        # Called from a YAML build definition, kicks off test runs to Azure ML Compute
        if params["job"] == START_BUILD:
            start_build_pipeline(params)

        # Called from a test run, updates telemetry in Azure DevOps and checks to close pipeline
        elif params["job"] == UPDATE_BUILD:
            update_build_pipeline(params)


def start_build_pipeline(params):
    rc_params = params["run_configuration"]

    # Downloads repository to snapshot and injects SB dependency
    fh.fetch_repository(
        rc_params["repository"]
    )
    fh.add_pip_dependency(
        rc_params["conda_file"],
        'azure-servicebus'
    )

    # Fetches Experiment to submit run on
    exp = ah.fetch_experiment(params)

    # Creates new runs in DevOps, injects code into notebooks, and submits them to the Experiment
    for notebook in rc_params["notebooks"]:

        response = rh.post_new_run(params, notebook)
        run_id = response.json()["id"]

        fh.add_notebook_callback(params, notebook, run_id)

        run = ah.submit_run(params, exp, notebook)
        run.tag(notebook)


def update_build_pipeline(params):

    exp = ah.fetch_experiment(params)
    # current_run = handlers.fetch_run(params, exp)

    # Updates Test Results
    rh.post_run_results(params, None) # current_run.get_details())

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
            rh.post_pipeline_callback(params, PIPELINE_FAILED)
        
        else:
            rh.post_pipeline_callback(params, PIPELINE_PASSED)
