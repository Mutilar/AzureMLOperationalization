import azure.functions as func
import yaml
import sys
sys.path.append("handlers")
import file_handler as fh
import azureml_handler as ah
import request_handler as rh

# Job types
START_BUILD = "!START"
UPDATE_BUILD = "!UPDATE"

# States of runs
FAILED_RUN = "Failed"
UNFINISHED_RUN = ["Queued", "Preparing", "Starting", "Running"]

# States of pipelines
PASSED_PIPELINE = "Succeeded"
FAILED_PIPELINE = "Failed"

def main(event: func.EventGridEvent):
    
    # TODO: Event-grid based wrap-up
    # Instead of all parameters getting passed via the JSON payload of the Event, 
    # only enough information to fetch the experiment and it's runs is needed for wrap-up. 
    params = event.get_json()
    
    # Updates telemetry in Azure DevOps, triggered from a Experiment Run
    update_build_pipeline(params)


def update_build_pipeline(params):

    exp = ah.fetch_experiment(params)
    # current_run = handlers.fetch_run(params, exp)

    # Updates Test Results
    rh.post_run_results(params, None) # current_run.get_details())

    # Checks if pipeline has finished all runs
    finished_count = 0
    notebook_failed = False
    for run in exp.get_runs():

        # If run is finished
        if not any(flag in str(run) for flag in UNFINISHED_RUN):
            finished_count += 1
        
        # If run failed
        if FAILED_RUN in str(run):
            notebook_failed = True

    # If all runs are finished, closes pipeline
    if finished_count == len(params["run_config"]["notebooks"]):
        if notebook_failed and params["run_condition"] == "all_pass":
            rh.post_pipeline_callback(params, FAILED_PIPELINE)
        else:
            rh.post_pipeline_callback(params, PASSED_PIPELINE)
