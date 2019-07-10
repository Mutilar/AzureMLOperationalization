import os 
import sys
import shutil
import fileinput
import requests
import io 
import zipfile
        

def fetch_repo(repo):
    snapshot_dir = os.getcwd() + "/snapshot"

    # Wipes snapshot directory, clearing out old files
    if os.path.exists(snapshot_dir):
        shutil.rmtree(snapshot_dir)

    # Recreates snapshot folder
    os.makedirs(snapshot_dir)

    # Moves to snapshot directory
    os.chdir(
        os.path.dirname(
            snapshot_dir
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
