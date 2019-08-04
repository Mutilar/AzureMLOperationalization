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
        conda_str = inject_pip_package(conda_str, requirement)

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


def add_notebook_callback(params, notebook, run_id, postexec=None, preexec=None):
    """ Enables notebooks to call back to the Azure Function.
    This is done to update the Pipeline based on Run results.
    """
    
    notebook_file_location = "./snapshot/inputs/" + notebook

    # Opens the notebook
    notebook_obj = nh.Notebook(
        get_file_str(notebook_file_location)
    )

    # Removes empty code cells
    notebook_obj.scrub_empty_cells()

    # Injecting post-execution code
    if postexec:
        if notebook in postexec:
            code = get_file_str("./staging/inputs/" + postexec[notebook]).split("\n")
            notebook_obj.inject_cell(
                position=nh.LAST_CELL,
                code=code
            )

    # Injecting pre-execution code
    if preexec:
        if notebook in preexec:
            code = get_file_str("./staging/inputs/" + preexec[notebook]).split("\n")
            notebook_obj.inject_cell(
                position=nh.FIRST_CELL,
                code=code
            )

    # Indents code to prepare for try catches
    notebook_obj.indent_code(
        cells=notebook_obj.get_cells(nh.EVERY_CELL)
    )

    # Injects try catches with failure callbacks
    notebook_obj.inject_code(
        cells=notebook_obj.get_cells(nh.EVERY_CELL),
        position=nh.BEGINNING_OF_CELL,
        code=[
            "try:"
        ]
    )
    notebook_obj.inject_code(
        cells=notebook_obj.get_cells(nh.EVERY_CELL),
        position=nh.END_OF_CELL,
        code=[
            "except Exception as e:",
            nh.TAB + "_queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)",
            nh.TAB + "_msg = Message(_params.replace(\"default_error_message\", str(e).replace(\"\\\'\",\"~\").replace(\"\\\"\",\"~\")))",
            nh.TAB + "_queue_client.send(_msg)",
            nh.TAB + "raise Exception(str(e))"
        ]
    )
    
    # Injects callback parameters
    notebook_obj.inject_code(
        cells=notebook_obj.get_cells(nh.FIRST_CELL),
        position=nh.BEGINNING_OF_CELL,
        code=[
            # "import os",
            # "os.chdir(os.path.join(os.getcwd(),\"inputs\",os.path.dirname(\""+notebook+"\")))",
            "#SP AUTHENTICATION",
            "import os",
            "from azureml._base_sdk_common.common import perform_interactive_login",
            "perform_interactive_login(",
            nh.TAB + "username=\"" + params["azure_resources"]["service_principal"]["username"] + "\",",  #os.environ[\"SP_USERNAME\"],",
            nh.TAB + "tenant=\"" + params["azure_resources"]["service_principal"]["tenant"]   + "\",",    #os.environ[\"SP_TENANT\"],",
            nh.TAB + "password=\"" + params["azure_resources"]["service_principal"]["password"] + "\",", #os.environ[\"SP_PASSWORD\"],",
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
    notebook_obj.inject_code(
        cells=notebook_obj.get_cells(nh.LAST_CELL),
        position=nh.END_OF_CELL,
        code=[
            "_queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)",
            "_msg = Message(_params.replace(\"default_error_message\",\"Ran successfully\"))",
            "_queue_client.send(_msg)"
        ]
    )

    # Scrub magic functions
    notebook_obj.scrub_magic_functions(
        cells=notebook_obj.get_cells(nh.EVERY_CELL)
    )

    # Injects callback parameters
    notebook_str = inject_notebook_params(
        str(notebook_obj),
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
    
    # Wipes staging directories, clearing out old files
    if os.path.exists(os.getcwd() + "/staging/"):
        shutil.rmtree(os.getcwd() + "/staging/")

    # Recreates staging folder
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


def fetch_requirements(notebook):
    """ Finds notebook's definition in a release.json file to determine dependencies and requirements. 
    """

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

                    if notebook_path == notebook:
                        return release_json["notebooks"][channel]
    return {}


def build_snapshot(notebook, dependencies, requirements, postexec, conda_file, ws_name, ws_subscription_id, ws_resource_group):
    """ Moves files-of-interest into snapshot folder to be run on Azure ML Compute.
    Also generates config files for "from_config" ML Workspaces. 
    """

    # Wipe any previous snapshot builds
    if os.path.exists(os.getcwd() + "/snapshot/"):
        shutil.rmtree(os.getcwd() + "/snapshot/")

    staging_file = os.path.join(
        "./staging/inputs",
        notebook
    )
    snapshot_path = os.path.join(
        "./snapshot/inputs",
        os.path.dirname(notebook)
    )

    if not os.path.exists(snapshot_path):
        os.makedirs(snapshot_path)

    # Moves notebook
    shutil.copy(
        staging_file,
        snapshot_path
    )

    # Adds notebook config file
    set_file_str(
        file_location=os.path.join(
            snapshot_path,
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

    # Moves and populates Conda File
    conda_staging_file = os.path.join(
        "./staging/inputs",
        conda_file
    )
    conda_snapshot_path = os.path.join(
        "./snapshot/inputs",
        os.path.dirname(conda_file)
    )
    shutil.copy(
        conda_staging_file,
        conda_snapshot_path
    )
    if not requirements:
        requirements = ["azure-servicebus", "azureml", "azureml-sdk"]
    else:
        requirements += ["azure-servicebus", "azureml", "azureml-sdk"]
    add_pip_packages(
        conda_file,
        requirements
    )

    if postexec:
        check_notebook_staging_file = os.path.join(
            "./staging/inputs",
            os.path.dirname(notebook),
            "checknotebookoutput.py"
        )
        check_experiment_staging_file = os.path.join(
            "./staging/inputs",
            os.path.dirname(notebook),
            "checkexperimentresult.py"
        )
        shutil.copy(
            check_notebook_staging_file,
            snapshot_path
        )
        shutil.copy(
            check_experiment_staging_file,
            snapshot_path
        )

    if dependencies:
        for dependency in dependencies:
            staging_file = os.path.join(
                "./staging/inputs",
                os.path.dirname(notebook),
                dependency
            )
            shutil.copy(
                staging_file,
                snapshot_path
            )
