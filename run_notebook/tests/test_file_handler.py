from ..run_notebook import file_handler as fh

# File Handler Unit Tests
# -----------------------

def test_parse_and_validate_parameters():

    params_input = f'./params/hello-world.json'

    assert fh.parse_and_validate_parameters(fh.get_file_str(params_input)) is not None


def test_add_service_bus_dependency():

    conda_input = f'./conda-files/inputs/hello-world.yml'
    conda_output = f'./conda-files/outputs/hello-world.yml'

    assert fh.add_service_bus_dependency(fh.get_file_str(conda_input)) == fh.get_file_str(conda_output)


def test_add_notebook_callback():

    notebook_input = f'./notebooks/inputs/hello-world.ipynb'
    notebook_output = f'./notebooks/outputs/hello-world.ipynb'

    assert fh.add_notebook_callback(fh.get_file_str(notebook_input)) == fh.get_file_str(notebook_output)