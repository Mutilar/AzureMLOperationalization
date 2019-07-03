# File directory management
import os 
import sys
import shutil
import fileinput
import json

# Fetching && Unzipping repositories
import requests
import io 
import zipfile
        
TAB = '    '

def get_file_str(file_location):
    with open(file_location, "r") as file:
        return file.read()
    return False


def set_file_str(file_location, output):
    with open(file_location, "w") as file:
        file.write(output)
        return True
    return False


def add_pip_dependency(conda_file, dependency):

    conda_file_location = f'./snapshot/inputs/{conda_file}'

    # Open the Conda file
    conda_str = get_file_str(conda_file_location)

    # Inject the azure servicebus pip dependency for callbacks
    conda_str = inject_pip_dependency(conda_str, dependency)

    # Writes changes to file
    set_file_str(conda_file_location, conda_str)


def inject_pip_dependency(file_str, dependency):
    return file_str.replace(
        '- pip:\n',
        f'- pip:\n  - {dependency}\n'
    )


def add_notebook_callback(params, notebook_location, run_id):

    notebook_file_location = f'./snapshot/inputs/{notebook_location}'

    # Opens the notebook
    notebook_str = get_file_str(notebook_file_location)

    # Injects try-catches
    notebook_str = inject_notebook_try_catches(notebook_str)

    # Injects params
    notebook_str = inject_notebook_params(notebook_str, params, run_id)
    
    # Writes changes to file
    set_file_str(notebook_file_location, notebook_str)

        
def inject_notebook_try_catches(notebook_str):

    output = []

    # String per line in the notebook 
    lines = notebook_str.split("\n")

    # Flow control variables
    found_code_cell = False
    found_code_source_beginning = False
    found_code_source = False

    # Tracks what code cell is currently being editted
    num_code_cells = 0
    cur_code_cell = 0

    # Counts number of code cells
    for i in range(0, len(lines)):
        if lines[i] == '   "cell_type": "code",':
            num_code_cells += 1
    
    # Iterates across notebook adding trys, catches, service bus messages
    for i in range(0, len(lines)):

        # If currently inside a code block
        if found_code_source:  

            # If the code block ends
            if lines[i] == '   ]':
                found_code_source = False

                # Add except statement, sending error message if errored
                output.append('    "except Exception as e:\\n",')
                output.append('    "    if HAS_ERRORED is False:\\n",')
                output.append('    "        _queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)\\n",')
                output.append('    "        _msg = Message(_params.replace(\\"default_error_message\\", str(e).replace(\\"\'\\",\\"\\")))\\n",')
                output.append('    "        _queue_client.send(_msg)\\n",')
                output.append('    "        HAS_ERRORED = True\\n",')   
                output.append('    "        raise Exception(e)\\n"')

                # If this is the final code block, send success message if never errored
                if cur_code_cell == num_code_cells:
                    output = output[:(len(output)-1)] + ','
                    output.append('    "if HAS_ERRORED is False:\\n",')
                    output.append('    "    _queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)\\n",')
                    output.append('    "    _msg = Message(_params.replace(\\"default_error_message\\",\\"Ran successfully\\"))\\n",')
                    output.append('    "    _queue_client.send(_msg)\\n"')

        # If just started a new code block
        elif found_code_source_beginning:
            found_code_source = True
            found_code_source_beginning = False
            cur_code_cell += 1

            # If first block, add global variables
            if cur_code_cell == 1:
                output.append('    "from azure.servicebus import QueueClient, Message\\n",')
                output.append('    "_connection_string = \\"!CONNECTION_STRING\\"\\n",')
                output.append('    "_queue_name = \\"!NAME\\"\\n",')
                output.append('    "_params = \'!PARAMS\'\\n",')
                output.append('    "HAS_ERRORED = False\\n",') 

            # Inject try statement
            output.append('    "try:\\n",')    

        # If inside code block header
        elif found_code_cell:

            # Found the code block source
            if lines[i] == '   "source": [':
                found_code_cell = False
                found_code_source_beginning = True
        
        # Found the beginning of a code block header
        elif lines[i] == '   "cell_type": "code",':
            found_code_cell = True

        # Push line to output, with some manipulation to add spacing for try-catch blocks, and adding commas/return lines when necessary
        if found_code_source:

            # If next line is the end of a code block, add a \n and , to end of line
            if lines[i+1] == '   ]':
                line_trimmed = lines[i][:5] + TAB + lines[i][5:]
                line_trimmed = line_trimmed[:(len(line_trimmed)-1)]
                output.append(line_trimmed + '\\n",')
                
            # Add spacing to any pre-existing code
            else:
                output.append(lines[i][:5] + TAB + lines[i][5:])
        else:
            # Leave the line untouched if it isn't inside a code block
            output.append(lines[i])
    
    return "\n".join(line for line in output)


def inject_notebook_params(notebook_str, params, run_id): 
    
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

#TODO: UNIT TEST
def fetch_repository(repository):

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

    # Downloads repository
    repo_zip = zipfile.ZipFile(
        io.BytesIO(
            requests.get(
                repository
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

    # Creates output folder
    os.makedirs("./outputs")

    # Returns to main directory
    os.chdir("..")


