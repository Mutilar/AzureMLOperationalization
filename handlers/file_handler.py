import os 
import sys
import shutil
import fileinput
import requests
import io
import json
import zipfile
import notebook_handler as nh


CONDA_FILE_LOCATION = "snapshot/inputs/environment.yml"


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

    # Open the Conda file
    conda_str = get_file_str(conda_file)

    # Inject the azure servicebus pip dependency for callbacks
    for requirement in requirements:
        conda_str = inject_pip_package(conda_str, requirement)

    # Writes changes to file
    set_file_str(conda_file, conda_str)


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
    
    notebook_file_location = os.path.join(
        "snapshot",
        "inputs",
        notebook
    )

    # Opens the notebook
    notebook_obj = nh.Notebook(
        get_file_str(notebook_file_location)
    )

    # Removes empty code cells
    notebook_obj.scrub_empty_cells()

    # Injecting post-execution code
    if postexec is not None:
        code = get_file_str(
            os.path.join(
                "staging",
                os.path.dirname(notebook),
                postexec
            )
        ).split("\n")
        notebook_obj.inject_cell(
            position=nh.LAST_CELL,
            code=code
        )

    # Injecting pre-execution code
    if preexec:
        code = get_file_str(
            os.path.join(
                "staging",
                os.path.dirname(notebook),
                preexec
            )
        ).split("\n")
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
            nh.TAB + "username=os.environ[\"SP_USERNAME\"],",
            nh.TAB + "tenant=os.environ[\"SP_TENANT\"],",
            nh.TAB + "password=os.environ[\"SP_PASSWORD\"],",
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
        cells=notebook_obj.get_cells(nh.EVERY_CELL),
        folder=os.path.dirname(notebook_file_location)
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


def prepare_staging(repo, root):
    """ Clones a GitHub repository locally into the snapshot folder.
    """
    
    base_directory = os.getcwd()

    # Wipes staging directories, clearing out old files
    if os.path.exists(base_directory + "/snapshot/"):
        shutil.rmtree(base_directory + "/snapshot/")

    # Recreates and enters staging folder
    os.makedirs(
        os.path.join(
            base_directory,
            "snapshot/"
        )
    )
    os.chdir(
        os.path.join(
            base_directory,
            "snapshot/"
        )
    )

    # Unzips repository
    zipfile.ZipFile(
        io.BytesIO(
            repo
        )
    ).extractall()

    os.rename(
        os.listdir()[0],
        "inputs"
    )

    shutil.copy(
        os.path.join(
        "generics",
        "environment.yml"
        ),
        CONDA_FILE_LOCATION
    )

    # Returns to main directory
    os.chdir("..")

def fetch_requirements(notebook):
    """ Finds notebook's definition in a release.json file to determine dependencies and requirements. 
    """

    for root, dirs, files in os.walk("./staging/"):
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
                            ).split("/")[2:]
                        )
                    else:
                        notebook_path = "/".join(
                            os.path.join(
                                root,
                                channel_notebook["name"]
                            ).split("/")[2:]
                        )

                    if notebook_path == notebook:
                        return release_json["notebooks"][channel]
    return {
        "celltimeout": 1200
    }


def build_snapshot(notebook, dependencies, requirements, postexec, conda_file, ws_name, ws_subscription_id, ws_resource_group):
    """ Moves files-of-interest into snapshot folder to be run on Azure ML Compute.
    Also generates config files for "from_config" ML Workspaces. 
    """

    # Wipes any previous snapshot builds
    if os.path.exists(os.getcwd() + "/snapshot/"):
        shutil.rmtree(os.getcwd() + "/snapshot/")

    staging_file = os.path.join(
        "staging",
        notebook
    )
    snapshot_path = os.path.join(
        "snapshot",
        "inputs",
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

    # if postexec:
    #     for post_exec_script in ["checknotebookoutput.py", "checkexperimentresult.py", "checkcelloutput.py"]:
    #         post_exec_file = os.path.join(
    #             "staging",
    #             os.path.dirname(notebook),
    #             post_exec_script
    #         )
    #         shutil.copy(
    #             post_exec_file,
    #             snapshot_path
    #         )

    if dependencies:
        for dependency in dependencies:
            staging_file = os.path.join(
                "staging",
                os.path.dirname(notebook),
                dependency
            )
            shutil.copy(
                staging_file,
                snapshot_path
            )

    # Moves and populates Conda File
    if conda_file:
        shutil.copy(
            os.path.join(
                "staging",
                conda_file
            ),
            CONDA_FILE_LOCATION
        )
    else:
        shutil.copy(
            os.path.join(
                "generics",
                "environment.yml"
            ),
            CONDA_FILE_LOCATION
        )
    if not requirements:
        requirements = ["azure-servicebus", "azureml", "azureml-sdk"]
    else:
        requirements += ["azure-servicebus", "azureml", "azureml-sdk"]
    
    add_pip_packages(
        CONDA_FILE_LOCATION,
        requirements
    )
