import sys
sys.path.append("handlers")

# File Handler Unit Tests
# -----------------------

import file_handler as fh

FILE_INPUT = "./unit_testing/hello_world.txt"

CONDA_INPUT = "./unit_testing/conda_files/inputs/hello_world.yml"
CONDA_OUTPUT = "./unit_testing/conda_files/outputs/hello_world.yml"

NOTEBOOK_INPUT = "./unit_testing/notebooks/inputs/hello_world.ipynb"
NOTEBOOK_OUTPUT = "./unit_testing/notebooks/outputs/hello_world.ipynb"


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
