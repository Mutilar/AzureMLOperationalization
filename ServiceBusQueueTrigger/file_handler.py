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
        

#TODO: UNIT TEST
def parse_and_validate_parameters(msg):

    # Cleans and formats string to be parsed into JSON 
    msg_str = str(msg.get_body().decode("utf-8")).replace('\'', '"')

    # try:
    return json.loads(msg_str)
    # except Exception as e:
    #     return None
    # Check to make sure all fields required are present...
    # not sure cleanest approach for this

#TODO: UNIT TEST...?
def add_service_bus_dependency(params):

    conda_file_location = f'./snapshot/inputs/{params["run_configuration"]["conda_file"]}'

    # Open the Conda file
    with open(conda_file_location, "r") as file:
        file_str = file.read()

    # Inject the azure servicebus pip dependency for callbacks
    file_str = file_str.replace('- pip:\n','- pip:\n  - azure-servicebus\n')

    # Writes changes to file
    with open(conda_file_location, "w") as file:
        file.write(file_str)

#TODO: UNIT TEST
def add_notebook_callback(params, notebook_name, count, replace_placeholders = True):

    notebook_file_location = f'./snapshot/inputs/{notebook_name}'

    # Open the notebook
    with open(notebook_file_location, "r") as file:
        file_str = file.read()
    
    # String per line in the notebook 
    lines = file_str.split("\n")
    output = ""

    # Flow control variables
    found_code_cell = False
    found_code_source_beginning = False
    found_code_source = False

    # Tracking what code cell is currently being editted
    num_code_cells = 0
    cur_code_cell = 0

    # Counting number of code cells
    for i in range(0, len(lines)):
        if lines[i] == '   "cell_type": "code",':
            num_code_cells += 1
    
    # Iterate across notebook adding trys, catches, service bus messages
    for i in range(0, len(lines)):

        # If currently inside a code block
        if found_code_source is True:  

            # If the code block ends
            if lines[i] == '   ]':

                found_code_source = False

                # Add except statement, sending error message if errored
                output += '    "except Exception as e:\\n",\n'
                output += '    "    if HAS_ERRORED is False:\\n",\n'
                output += '    "        _queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)\\n",\n'
                output += '    "        _msg = Message(_params.replace(\\"default_error_message\\", str(e).replace(\\"\'\\",\\"\\")))\\n",\n'
                output += '    "        _queue_client.send(_msg)\\n",\n'
                output += '    "        HAS_ERRORED = True\\n",\n'   
                output += '    "        raise Exception(e)\\n"\n'

                # If this is the final code block, send success message if never errored
                if cur_code_cell == num_code_cells:
                    output = output[:(len(output)-1)] + ',\n'
                    output += '    "if HAS_ERRORED is False:\\n",\n'
                    output += '    "    _queue_client = QueueClient.from_connection_string(_connection_string, _queue_name)\\n",\n'
                    output += '    "    _msg = Message(_params.replace(\\"default_error_message\\",\\"Ran successfully\\"))\\n",\n'
                    output += '    "    _queue_client.send(_msg)\\n"\n'

        # If just started a new code block
        elif found_code_source_beginning is True:

            found_code_source = True
            found_code_source_beginning = False
            cur_code_cell += 1

            # If first block, add global boolean
            if cur_code_cell == 1:
                output += '    "from azure.servicebus import QueueClient, Message\\n",\n'
                output += '    "_connection_string = \\"!CONNECTION_STRING\\"\\n",\n'
                output += '    "_queue_name = \\"!NAME\\"\\n",\n'
                output += '    "_params = \'!PARAMS\'\\n",\n'
                output += '    "HAS_ERRORED = False\\n",\n' 

            # Inject try statement
            output += '    "try:\\n",\n'    

        # If inside code block header
        elif found_code_cell is True:

            # Found the code block source
            if lines[i] == '   "source": [':
                found_code_cell = False
                found_code_source_beginning = True
        
        # Found the beginning of a code block header
        elif lines[i] == '   "cell_type": "code",':
            found_code_cell = True

        # Push line to output, with some manipulation to add spacing for try-catch blocks, and adding commas/return lines when necessary
        if found_code_source is True:
            split_index = 5

            # If next line is the end of a code block, add a \n and , to end of line
            if lines[i+1] == '   ]':
                output_to_be_truncated = lines[i][:split_index] + '    ' + lines[i][split_index:]
                output_to_be_truncated = output_to_be_truncated[:(len(output_to_be_truncated)-1)]
                output += output_to_be_truncated + '\\n",\n'
                
            # Add spacing to any pre-existing code
            else:
                output += lines[i][:split_index] + '    ' + lines[i][split_index:] + '\n'
        else:

            # Leave the line untouched if it isn't inside a code block
            output += lines[i] + '\n'

    # Injects Service Bus Queue parameters
    output = output.replace("!CONNECTION_STRING", params["wrap_up"]["queue"]["connection_string"])
    output = output.replace("!NAME", params["wrap_up"]["queue"]["name"])
    
    # Injects parameters, updating relevant fields
    output = output.replace("!PARAMS", f'{params}'.replace('\'','\\"').replace('!START','!UPDATE').replace('default_run_id',f'{count}'))
    
    # Writes changes to file
    with open(notebook_file_location, 'w') as file:
        file.write(output)


#TODO: UNIT TEST
def fetch_repository(params):

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
                params["run_configuration"]["repository"]
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
