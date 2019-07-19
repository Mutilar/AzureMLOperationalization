import azure.functions as func
from yaml import safe_load as load
from base64 import b64encode as encode
from time import sleep
import sys
sys.path.append("handlers")
import file_handler as fh
import azureml_handler as ah
import devops_handler as dh

# Job types
START_BUILD = "!START"
UPDATE_BUILD = "!UPDATE"

# States of pipelines
PASSED_PIPELINE = "Succeeded"
FAILED_PIPELINE = "Failed"

# Run Conditions for pipelines
ALL_NOTEBOOKS_MUST_PASS = "all_pass"

# Directories
OUTPUT_NOTEBOOK_LOCATION = "snapshot/outputs/output.ipynb"

def main(msg: func.ServiceBusMessage):

    # Converts bytes into JSON
    # https://docs.microsoft.com/en-us/python/api/azure-functions/azure.functions.servicebusmessage?view=azure-python

    try:
        params = load(
            msg.get_body().decode("utf-8")
        )
    except Exception as e:  
        raise Exception(str(e) + str(msg.get_body().decode("utf-8")))

    raise Exception (params)
