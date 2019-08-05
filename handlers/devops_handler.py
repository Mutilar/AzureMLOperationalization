import requests


def post_pipeline_callback(result, plan_url, organization, project_id, hub_name, plan_id, task_id, job_id, auth_token):
    return requests.post(
        get_pipeline_callback_url(plan_url, organization, project_id, hub_name, plan_id),
        json=get_pipeline_callback_json(result, task_id, job_id),
        headers=get_auth_header(auth_token)
    )


def post_new_run(notebook, plan_url, organization, project, build_id,  auth_token):
    return requests.post(
        get_new_run_url(plan_url, organization, project),
        json=get_new_run_json(build_id, notebook),
        headers=get_auth_header(auth_token)
    )


def patch_run_update(error_message, plan_url, organization, project, run_id, auth_token):
    return requests.patch(
        get_run_update_url(plan_url, organization, project, run_id),
        json=get_run_update_json(error_message),
        headers=get_auth_header(auth_token)
    )


def post_run_attachment(file_name, stream, plan_url, organization, project, run_id, auth_token):
    return requests.post(
        get_run_attachment_url(plan_url, organization, project, run_id),
        json=get_run_attachment_json(file_name, stream),
        headers=get_auth_header(auth_token)
    )


def post_run_results(error_message, run_details, plan_url, organization, project, run_id, auth_token):
    return requests.post(
        get_run_results_url(plan_url, organization, project, run_id),
        json=get_run_results_json(error_message, run_details),
        headers=get_auth_header(auth_token)
    )

def get_repository(root, version, auth_token):
    res = requests.get(
        get_repository_url(root,version),
        headers=get_auth_header(auth_token)
    )
    if res.status_code == 200:
        return res
    else:
        raise Exception("Couldn't fetch repository")


def get_pipeline_callback_url(plan_url, organization, project_id, hub_name, plan_id):
    return f'{plan_url}{organization}/{project_id}/_apis/distributedtask/hubs/{hub_name}/plans/{plan_id}/events?api-version=2.0-preview.1'


def get_new_run_url(plan_url, organization, project):
    return f'{plan_url}{organization}/{project}/_apis/test/runs?api-version=5.0'


def get_run_update_url(plan_url, organization, project, run_id):
    return f'{plan_url}{organization}/{project}/_apis/test/runs/{run_id}?api-version=5.0' 


def get_run_attachment_url(plan_url, organization, project, run_id):
    return f'{plan_url}{organization}/{project}/_apis/test/Runs/{run_id}/attachments?api-version=5.0-preview.1'


def get_run_results_url(plan_url, organization, project, run_id):
    return f'{plan_url}{organization}/{project}/_apis/test/Runs/{run_id}/results?api-version=5.0'


def get_repository_url(root, version):
    return f'https://msdata.visualstudio.com/DefaultCollection/3adb301f-9ede-41f2-933b-fcd1a486ff7f/_apis/git/repositories/1f1e7f17-65c5-4d5a-a5fa-487802b4e71b/Items?path=/{root}&versionDescriptor[versionOptions]=0&versionDescriptor[versionType]=0&versionDescriptor[version]={version}&resolveLfs=true&$format=zip&api-version=5.0-preview.1'


def get_pipeline_callback_json(result, task_id, job_id):
    return {
        'name': 'TaskCompleted',
        'taskId': task_id,
        'jobId': job_id,
        'result': result
    }


def get_new_run_json(build_id, notebook):
    return {
        'name': f'Executing {notebook}',
        'state': 'InProgress',
        'automated': 'true',
        'build': {
            'id': build_id
        }
    }


def get_run_update_json(error_message):
    outcome = 'Completed' if error_message == 'Ran successfully' else 'Aborted'
    return {
        'state': outcome,
        'comment': error_message,
    }
    

def get_run_attachment_json(file_name, stream):
    return {
        'fileName': file_name,
        'stream': stream,
        'comment': 'Resulting notebook from Azure ML Compute',
        'attachmentType': 'GeneralAttachment'
    }


def get_run_results_json(error_message, run_details):
    outcome = 'Passed' if error_message == 'Ran successfully' else 'Failed'
    return [
        {
            'testCaseTitle': 'Run Notebook',
            'automatedTestName': 'TestName',
            'priority': 1,
            'createdDate': run_details['startTimeUtc'],
            'startedDate': run_details['startTimeUtc'],
            'completedDate': run_details['endTimeUtc'],
            'errorMessage': error_message,
            'outcome': outcome
        }
    ]


def get_auth_header(auth_token):
    return {
        'Authorization': f'Bearer {auth_token}'
    }
