import os 
import sys
import shutil
import fileinput
import requests
import io 
import zipfile
        

def fetch_repo(repo):

    # Wipes snapshot directory, clearing out old files
    if os.path.exists(os.getcwd() + "/snapshot"):
        shutil.rmtree(os.getcwd() + "/snapshot")

    # Recreates snapshot folder
    os.makedirs(os.getcwd() + "/snapshot")

    # Moves to snapshot directory
    os.chdir(
        os.path.dirname(
            "snapshot"
        )
    )

    # Downloads repository
    repo_zip = zipfile.ZipFile(
        io.BytesIO(
            requests.get(
                repo
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
    os.makedirs("outputs")

    # Returns to main directory
    os.chdir("..")
