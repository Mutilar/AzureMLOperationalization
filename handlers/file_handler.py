import os 
import sys
import shutil
import fileinput
import requests
import io 
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


def add_pip_dependencies(conda_file, dependencies):
    """ Adds a new pip dependency to a given conda file.
    """

    conda_file_location = "./snapshot/inputs/" + conda_file

    # Open the Conda file
    conda_str = get_file_str(conda_file_location)

    # Inject the azure servicebus pip dependency for callbacks
    for dependency in dependencies:
        conda_str = inject_pip_dependency(conda_str, dependency)

    # Writes changes to file
    set_file_str(conda_file_location, conda_str)


def inject_pip_dependency(file_str, dependency):
    return file_str.replace(
        "- pip:\n",
        "- pip:\n  - " + dependency + "\n"
    )


def add_notebook_callback(params, notebook, run_id):
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

    notebook.inject_cell(
        position=nh.FIRST_CELL,
        code=[
            "print(\"hello\")"
        ]
    )
    notebook.inject_cell(
        position=nh.LAST_CELL,
        code=[
            "print(\"world\")"
        ]
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
    
    # Wipes snapshot directory, clearing out old files
    if os.path.exists(os.getcwd() + "/snapshot/"):
        shutil.rmtree(os.getcwd() + "/snapshot/")

    # Recreates snapshot folder
    os.makedirs(os.getcwd() + "/snapshot/")

    # Moves to snapshot directory
    os.chdir(
        os.path.dirname(
            "./snapshot/"
        )
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
