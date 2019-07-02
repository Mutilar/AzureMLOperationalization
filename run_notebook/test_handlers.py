# File Handler Unit Tests
# -----------------------

from . import file_handler as fh


def test_parse_and_validate_parameters():

    params_input = "./run_notebook/tests/params/hello-world.json"

    assert fh.parse_and_validate_parameters(fh.get_file_str(params_input)) is not None


def test_inject_pip_dependency():

    conda_input = "./run_notebook/tests/conda-files/inputs/hello-world.yml"
    conda_output = "./run_notebook/tests/conda-files/outputs/hello-world.yml"

    assert fh.inject_pip_dependency(fh.get_file_str(conda_input), "test-pip-dependency") == fh.get_file_str(conda_output)


def test_inject_notebook_try_catches():

    notebook_input = "./run_notebook/tests/notebooks/inputs/hello-world.ipynb"
    notebook_output = "./run_notebook/tests/notebooks/outputs/hello-world.ipynb"

    assert fh.inject_notebook_try_catches(fh.get_file_str(notebook_input)) == fh.get_file_str(notebook_output)