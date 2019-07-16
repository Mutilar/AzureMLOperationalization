import sys
sys.path.append("handlers")


# File Handler Unit Tests
# -----------------------

import file_handler as fh

FILE_INPUT = "./tests/hello-world.txt"

CONDA_INPUT = "./tests/conda-files/inputs/hello-world.yml"
CONDA_OUTPUT = "./tests/conda-files/outputs/hello-world.yml"

NOTEBOOK_INPUT = "./tests/notebooks/inputs/hello-world.ipynb"
NOTEBOOK_OUTPUT = "./tests/notebooks/outputs/hello-world.ipynb"


def test_get_file_str():

    assert fh.set_file_str(
        FILE_INPUT,
        "hello world"
    )

    assert fh.get_file_str(
        FILE_INPUT
    ) == "hello world"


def test_inject_pip_dependency():

    assert fh.inject_pip_dependency(
        fh.get_file_str(CONDA_INPUT),
        "test-pip-dependency"
    ) == fh.get_file_str(CONDA_OUTPUT)


def test_notebook_try_catches():

    assert fh.inject_notebook_try_catches(
        fh.get_file_str(NOTEBOOK_INPUT)
    ) == fh.get_file_str(NOTEBOOK_OUTPUT)

    assert fh.scrub_notebook_try_catches(
        fh.get_file_str(NOTEBOOK_OUTPUT)
    ) == fh.get_file_str(NOTEBOOK_INPUT)

    assert fh.inject_notebook_try_catches(
        fh.scrub_notebook_try_catches(
            fh.get_file_str(NOTEBOOK_OUTPUT)
        )
    ) == fh.get_file_str(NOTEBOOK_OUTPUT)

    assert fh.scrub_notebook_try_catches(
        fh.inject_notebook_try_catches(
            fh.get_file_str(NOTEBOOK_INPUT)
        )
    ) == fh.get_file_str(NOTEBOOK_INPUT)


# Request Handler Unit Tests
# -----------------------

import devops_handler as dh


# TODO:: validate json, url, header auth functions with example params