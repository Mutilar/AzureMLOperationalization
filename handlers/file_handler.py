import os 
import sys
import shutil
import fileinput
import requests
import io
import json
import zipfile
import notebook_handler as nh


def get_file_str(file_location):
    """ Reads a file
    """
    
    with open(file_location, "r") as file:
        return file.read()
    return False


def set_file_str(file_location, output):
    """ Writes a string to a file
    """

    with open(file_location, "w") as file:
        file.write(output)
        return True
    return False


def add_pip_packages(conda_file, requirements):
    """ Adds a new pip dependency to a given conda file.
    """

    conda_file_location = "./snapshot/inputs/" + conda_file

    # Open the Conda file
    conda_str = get_file_str(conda_file_location)

    # Inject the azure servicebus pip dependency for callbacks
    for requirement in requirements:
        conda_str = inject_pip_dependency(conda_str, requirement)

    # Writes changes to file
    set_file_str(conda_file_location, conda_str)


def inject_pip_package(file_str, requirement):

    # It should only inject if the package isn't already added.
    if (" " + requirement + "\n") in file_str:
        return file_str
    if (" " + requirement + "==") in file_str:
        return file_str

    return file_str.replace(
        "- pip:\n",
        "- pip:\n  - " + requirement + "\n"
    )


def add_notebook_callback(params, notebook, run_id, postexecs, preexecs):
    """ Enables notebooks to call back to the Azure Function.
    This is done to update the Pipeline based on Run results.
    """
    
    notebook_file_location = "./snapshot/inputs/" + notebook

    # Opens the notebook
    notebook = nh.Notebook(
        get_file_str(notebook_file_location)
    )
    
    # Indents code to prepare for try catches
    notebook.indent_code(
        cells=notebook.get_cells(nh.EVERY_CELL)
    )

    # Injects try catches with failure callbacks
    notebook.inject_code(
        cells=notebook.get_cells(nh.EVERY_CELL),
        position=nh.BEGINNING_OF_CELL,
        code=[
            "try:"
        ]
    )
    notebook.inject_code(
        cells=notebook.get_cells(nh.EVERY_CELL),
        position=nh.END_OF_CELL,
        code=[
            "except Exception as e:",
            nh.TAB + "_queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)",
            nh.TAB + "_msg = Message(_params.replace(\"default_error_message\", str(e).replace(\"\\\'\",\"\\\"\")))",
            nh.TAB + "_queue_client.send(_msg)",
            nh.TAB + "raise Exception(e)"
        ]
    )
    
    # Injects callback parameters
    notebook.inject_code(
        cells=notebook.get_cells(nh.FIRST_CELL),
        position=nh.BEGINNING_OF_CELL,
        code=[
            "#SP AUTHENTICATION",
            "from azureml._base_sdk_common.common import perform_interactive_login",
            "perform_interactive_login(",
            nh.TAB + "username=\"" + params["azure_resources"]["service_principal"]["username"] + "\",",
            nh.TAB + "tenant=\"" + params["azure_resources"]["service_principal"]["tenant"] + "\",",
            nh.TAB + "password=\"" + params["azure_resources"]["service_principal"]["password"] + "\",",
            nh.TAB + "service_principal=True",
            ")",
            "#CALLBACK PARAMETERS",
            "from azure.servicebus import QueueClient, Message",
            "_connection_string = \'!CONNECTION_STRING\'",
            "_queue_name = \'!NAME\'",
            "_params = \'!PARAMS\'",
        ]
    )

    # Injects success callback
    notebook.inject_code(
        cells=notebook.get_cells(nh.LAST_CELL),
        position=nh.END_OF_CELL,
        code=[
            "_queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)",
            "_msg = Message(_params.replace(\"default_error_message\",\"Ran successfully\"))",
            "_queue_client.send(_msg)"
        ]
    )

    # Injecting post-execution code
    if notebook in postexecs:
        code = get_file_str("./staging/inputs/" + postexecs[notebook]).split("\n")
        notebook.inject_cell(
            position=nh.LAST_CELL,
            code=code
        )

    # Injecting pre-execution code
    if notebook in preexecs:
        code = get_file_str("./staging/inputs/" + preexecs[notebook]).split("\n")
        notebook.inject_cell(
            position=nh.FIRST_CELL,
            code=code
        )

    # Injects callback parameters
    notebook_str = inject_notebook_params(
        str(notebook),
        params,
        run_id
    )
    
    # Writes changes to file
    set_file_str(notebook_file_location, notebook_str)


def remove_notebook_callback(notebook_file_location):
    """ Removes all injected notebook code for previewing output notebook.
    """

    # Opens the notebook
    notebook = nh.Notebook(
        get_file_str(notebook_file_location)
    )
    
    # Removes injected code
    notebook.scrub_code(
        notebook.get_cells(nh.EVERY_CELL)
    )

    # Removes indentation (should only be called if "indent_code" is called previously)
    notebook.unindent_code(
        notebook.get_cells(nh.EVERY_CELL)
    )

    # Scrubs try-catches and returns string
    return str(notebook)


def inject_notebook_params(notebook_str, params, run_id): 
    """ Overrides placeholder string snippets with necessary parameters for callbacks.
    """

    # Injects Service Bus Queue parameters
    output = notebook_str.replace(
        "!CONNECTION_STRING",
        params["wrap_up"]["queue"]["connection_string"]
    ).replace(
        "!NAME",
        params["wrap_up"]["queue"]["name"]
    )
    
    # Updates params fields for callback
    callback_params = str(params).replace(
        "\'",
        "\\\""
    ).replace(
        "!START",
        "!UPDATE"
    ).replace(
        "default_run_id",
        str(run_id)
    )

    # Injects parameters, updating relevant fields
    output = output.replace(
        "!PARAMS",
        callback_params
    )

    return output


def fetch_repo(repo, version):
    """ Clones a GitHub repository locally into the snapshot folder.
    """
    
    # Wipes snapshot and staging directories, clearing out old files
    if os.path.exists(os.getcwd() + "/snapshot/"):
        shutil.rmtree(os.getcwd() + "/snapshot/")
    if os.path.exists(os.getcwd() + "/staging/"):
        shutil.rmtree(os.getcwd() + "/staging/")

    # Recreates snapshot and staging folders
    os.makedirs(os.getcwd() + "/snapshot/")
    os.makedirs(os.getcwd() + "/snapshot/inputs/")
    os.makedirs(os.getcwd() + "/staging/")

    # Moves to snapshot directory
    os.chdir(
        os.getcwd() + "/staging/"
    )

    # Downloads version of a repository
    #   version can be a branch name (e.g. "master", "dev")
    #   or commit hash (e.g. "bb7ad65dbc727ec09fe0613d51ce8585087de1b1")
    repo_zip = zipfile.ZipFile(
        io.BytesIO(
            requests.get(
                repo + "/archive/" + version + ".zip"
            ).content
        )
    )

    # Extracts repository
    repo_zip.extractall()

    # Renames repository to "inputs"
    os.rename(
        os.listdir(os.getcwd())[0],
        "inputs"
    )

    # Returns to main directory
    os.chdir("..")



def fetch_requirements(changed_notebooks):

    rq_params = {
        "requirements": [],
        "dependencies": [],
        "postexec": {},
        "preexec": {}
    }

    requirements = set([])
    dependencies = set([])

    for root, dirs, files in os.walk("./staging/inputs/"):
        for file in files:
            if file == "release.json":
                release_json = json.loads(
                    get_file_str(
                        os.path.join(root, file)
                    )
                )
                for channel in release_json["notebooks"]:
                    channel_notebook = release_json["notebooks"][channel]
                    notebook_path = ""
                    if "path" in channel_notebook:
                        notebook_path = "/".join(
                            os.path.join(
                                root,
                                os.path.join(
                                    channel_notebook["path"],
                                    channel_notebook["name"]
                                )
                            ).split("/")[3:]
                        )
                    else:
                        notebook_path = "/".join(
                            os.path.join(
                                root,
                                channel_notebook["name"]
                            ).split("/")[3:]
                        )
                    if notebook_path in changed_notebooks:

                        # Add pip package requirements to set
                        if "requirements" in release_json["notebooks"][channel]:
                            for requirement in release_json["notebooks"][channel]["requirements"]:
                                requirements.add(requirement)

                        # Add local file dependencies to set
                        if "dependencies" in release_json["notebooks"][channel]:
                            for dependency in release_json["notebooks"][channel]["dependencies"]:
                                dependencies.add(os.path.dirname(notebook_path) + dependency)

                        # Manage post- and pre-execution code preparation
                        if "postexec" in release_json["notebooks"][channel]:
                            rq_params["postexec"][notebook_path] = os.path.dirname(notebook_path) + release_json["notebooks"][channel]["postexec"]
                        if "preexec" in release_json["notebooks"][channel]:
                            rq_params["preexec"][notebook_path] = os.path.dirname(notebook_path) + release_json["notebooks"][channel]["preexec"]
    
    rq_params["requirements"] = list(requirements)
    rq_params["dependencies"] = list(dependencies)

    return rq_params


def build_snapshot(changed_notebooks, dependencies, ws_name, ws_subscription_id, ws_resource_group):
    

    for notebook in changed_notebooks:

        # Move notebook
        os.rename(
            os.getcwd() + "/staging/inputs/" + notebook,
            os.getcwd() + "/snapshot/inputs/" + notebook
        )

        # Add Notebook config file
        set_file_str(
            file_location=os.path.join(
                os.path.dirname("./snapshot/inputs/" + notebook),
                'config.json'
            ),
            output=json.dumps(
                {
                    'subscription_id': ws_subscription_id,
                    'resource_group': ws_resource_group,
                    'workspace_name': ws_name
                }
            )
        )

    for dependency in dependencies:
        os.rename(
            "./staging/inputs/" + dependency,
            "./snapshot/inputs/" + dependency
        )
