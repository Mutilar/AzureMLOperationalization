import requests

        
def post_pipeline_callback(params, result):
    # https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/utility/http-rest-api?view=azure-devops#where-should-a-task-signal-completion-when-callback-is-chosen-as-the-completion-event
    cb_params = params["wrap_up"]["call_back"]

    return requests.post(
        get_pipeline_callback_url(cb_params),
        json=get_pipeline_callback_json(cb_params, result),
        headers=get_auth_header(params["auth_token"])
    )


def post_new_run(params, notebook_name):
    # https://docs.microsoft.com/en-us/rest/api/azure/devops/test/runs/create?view=azure-devops-rest-5.0
    az_params = params["azure_resources"]

    return requests.post(
        get_new_run_url(az_params),
        json=get_new_run_json(params["build_id"], notebook_name),
        headers=get_auth_header(params["auth_token"])
    )


def post_run_results(params, run_properties):
    # https://docs.microsoft.com/en-us/rest/api/azure/devops/test/results/add?view=azure-devops-rest-5.0#shallowreference
    az_params = params["azure_resources"]
    cb_params = params["wrap_up"]["call_back"]

    return requests.post(
        get_run_results_url(az_params),
        json=get_run_results_json(cb_params, run_properties),
        headers=get_auth_header(params["auth_token"])
    )


def get_pipeline_callback_url(cb_params):
    return f'{cb_params["plan_url"]}{cb_params["project_id"]}/_apis/distributedtask/hubs/{cb_params["hub_name"]}/plans/{cb_params["plan_id"]}/events?api-version=2.0-preview.1'


def get_new_run_url(az_params):
    return f'https://dev.azure.com/{az_params["organization"]}/{az_params["project"]}/_apis/test/runs?api-version=5.0'


def get_run_results_url(az_params):
    return f'https://dev.azure.com/{az_params["organization"]}/{az_params["project"]}/_apis/test/Runs/{az_params["run_id"]}/results?api-version=5.0'


def get_pipeline_callback_json(cb_params, result):
    return {
        'name': 'TaskCompleted',
        'taskId': cb_params["task_id"],
        'jobId': cb_params["job_id"],
        'result': result
    }


def get_new_run_json(experiment_name, notebook_name):
    return {
        'name': f'Executing {notebook_name}',
        'state': 'InProgress',
        'automated': 'true',
        'build': {
            'id': experiment_name
        }
    }


def get_run_results_json(cb_params, run_properties):
    # TODO: run properties contains runtime information
    outcome = 'Passed' if cb_params["error_message"] == 'Ran successfully' else 'Failed'
    return [
        {
            'testCaseTitle': 'Run Notebook',
            'automatedTestName': 'TestName',
            'priority': 1,
            'errorMessage': cb_params["error_message"],
            'outcome': outcome
        }
    ]


def get_auth_header(auth_token):
    return {
        'Authorization': f'Bearer {auth_token}'
    }