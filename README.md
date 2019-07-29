
# Azure ML Operationalization

[![Build Status](https://dev.azure.com/t-brhung/brhung-test-pipeline/_apis/build/status/Mutilar.brhung-deployment-testing?branchName=master)](https://dev.azure.com/t-brhung/brhung-test-pipeline/_build/latest?definitionId=8&branchName=master)

Streamlining and expediting a data scientist's CI/CD workflow leveraging prebaked functionalities of Azure DevOps Pipelines, Azure Functions, and Azure Service Bus Queues.

### Key aspects:
- [Azure DevOps Pipelines](https://azure.microsoft.com/en-us/services/devops/pipelines/)
- [Azure Service Bus](https://azure.microsoft.com/en-us/services/service-bus/)
- [Azure Functions](https://azure.microsoft.com/en-us/services/functions/)
- [Azure Machine Learning](https://azure.microsoft.com/en-us/services/machine-learning-service/)

Azure Python Functions can cleanly interact with the Azure ML SDK and can be easily integrated into Azure DevOps Pipelines. 

### Core dependencies:
- [Python 3.6.8][download-python]
- [Azure Functions Core Tools][functions-run-local]
- [Azure CLI][install-azure-cli]
- [Azure ML SDK + Contrib][install-azure-ml-sdk]

# The File Directory

> - RunNotebookFunctionApp
> > - run_notebook_service_bus
> > > - ```__init__.py```
> > > - ```function.json```
> > - handlers
> > > - ```azureml_handler.py```
> > > - ```devops_handler.py```
> > > - ```file_handler.py```
> > > - ```notebook_handler.py```
> > - unit_testing
> > > - ```test_handlers.py```
> > - ```deployment_pipeline.yml```
> > - ```requirements.txt``` 

## ```deployment_pipeline.yml```

This file controls the CD pipeline for the Function App. It functions with two main stages: 

> #### ```Deployment```
> 
> This agent-based stage prepares the deployment environment, unit-tests, bundles, and  finally deploys the Azure Function Application. Simplified, it looks like this:
>
> ```yml
> - stage: Deployment
>   jobs:
>   - job: 
>     pool:
>       vmImage: 'ubuntu-16.04'
>     steps:
>     - task: UsePythonVersion@0
>     - bash: pip3.6 install -r requirements.txt
>     - bash: pytest
>     - task: ArchiveFiles@2
>     - task: AzureFunctionApp@1
> ```
 
> #### ```Validation```
>
> This agentless stage validates the changes by running a controlled job through the new deployment of the application to ensure everything is functioning as expected. Simplified, it looks like this:
> 
> ```yml
> - stage: Validation
>   jobs:
>   - job: 
>     pool: server
>     steps:
>     - task: RunNotebookTest@1
> ```


## ```requirements.txt```

This file controls the dependencies required for the Azure Function. This is mainly the Azure ML SDK, its associated dependencies, and support for HTTP requests, file system manipulation, etc.

```
...
azureml==0.2.7
azureml-contrib-notebook==1.0.43
azureml-core==1.0.43
azureml-pipeline==1.0.43
azureml-sdk==1.0.43
...
```

When deploying the function app, these are injected into the package, as seem in the deployment YAML file:

```
pip3.6 install -r requirements.txt
```

## ```run_notebook_service_bus/function.json```

This file specifies the location of main function (e.g. ```__init__.py```), as well as the Service Bus binding for the function.

## ```run_notebook_service_bus/__init__.py```

This script holds all the pythonic logic of the application. The main function is short, favoring a helper function to handle the distinct job types: ```start_build_pipeline()``` and ```update_build_pipeline()```. 

> #### ```start_build_pipeline()```
> 
> Fetches the repository of interest, creates a new Experiment SDK Object, and submits a set of notebook Runs to that object after injecting try-catch statements to facilitate callbacks to the DevOps pipeline.

> #### ```update_build_pipeline()```
> 
> Updates the DevOps Test Runs based on results from Azure ML Compute, and checks to close the pipeline in all Runs are completed.

## ```handlers/azureml_handler.py```

This script handles all Azure ML SDK-related logic, including ```fetch_exp()```, ```fetch_run_config()```, and ```submit_run()```, which all manage Azure ML Workspace-related tasks.

> #### ```fetch_experiment()```
> 
> This function authenticates with the ML Workspace with a Service Principal connection, fetches the [Workspace](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.workspace(class)?view=azure-ml-py), and then fetches and returns a new [Experiment](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.experiment.experiment?view=azure-ml-py).

> #### ```fetch_run_config()```
>
> This function generates a [RunConfiguration](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.runconfiguration?view=azure-ml-py) based on the pipeline parameters, specifying such things as the [ComputeTarget](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.computetarget?view=azure-ml-py) and [CondaDependencies](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.conda_dependencies.condadependencies?view=azure-ml-py). More flexible of Run configurations can easily be implemented. 

> #### ```submit_run()```
>
> This function [submits a new Run](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.experiment(class)?view=azure-ml-py#submit-config--tags-none----kwargs-) with configurations based on the pipeline parameters.

> #### ```fetch_run()```
>
> This function [fetches a Run by its RunID tag](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.experiment.experiment?view=azure-ml-py#get-runs-type-none--tags-none--properties-none--include-children-false-) specified by the DevOps Test Run. 

> #### ```fetch_exp_status()```
>
> This function determines the status of the pipeline by [fetching all Runs](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.experiment.experiment?view=azure-ml-py#get-runs-type-none--tags-none--properties-none--include-children-false-) and [checking their status](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.run.run?view=azure-ml-py#get-status--)

## ```handlers/devops_handler.py```

This script handles all DevOps related tasks, including ```post_pipeline_callback()```, ```post_new_run()```, ```patch_run_update()```, and ```post_run_results()```.

> #### ```post_pipeline_callback()```
> 
> This function, along with its helper functions, [closes the DevOps Pipeline](https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/utility/http-rest-api?view=azure-devops#where-should-a-task-signal-completion-when-callback-is-chosen-as-the-completion-event) via the DevOps API.

> #### ```post_new_run()```
>
> This function, along with its helper functions, [creates a new DevOps Test Run](https://docs.microsoft.com/en-us/rest/api/azure/devops/test/runs/create?view=azure-devops-rest-5.0) via the DevOps API.

> #### ```patch_run_update()```
>
> This function, along with its helper functions, [updates a DevOps Test Run](https://docs.microsoft.com/en-us/rest/api/azure/devops/test/runs/update?view=azure-devops-rest-5.0) via the DevOps API.

> #### ```post_run_attachment()```
>
> This function, along with its helper functions, [uploads a DevOps Test Run Attachment](https://docs.microsoft.com/en-us/rest/api/azure/devops/test/Attachments/Create%20Test%20Run%20Attachment?view=azure-devops-rest-5.0) via the DevOps API. 

> #### ```post_run_results()```
>
> This function, along with its helper functions, [adds a DevOps Test Run Result](https://docs.microsoft.com/en-us/rest/api/azure/devops/test/results/add?view=azure-devops-rest-5.0) with result telemetry via the DevOps API.

## ```handlers/file_handler.py```

This script handles all file IO related tasks, including ```fetch_repo()```, ```add_pip_dependency()```, and ```add_notebook_callback()```.

> #### ```fetch_repo()```
>
> This function pulls and extracts repositories from GitHub to be submitted in a Run's snapshot folder.

> #### ```add_pip_dependency()```
>
> This function injects pip dependencies into the Conda file specified in the pipeline parameters.

> #### ```add_notebook_callback()```
>
> This function adds try-catches around each code-block of a notebook with callbacks to re-trigger the Azure Function when the notebook is finished running. 
> 
> *Note: this is a not an "ideal" solution from an architectural perspective, but a more platform-level, agnostic approach (e.g. with Event Grid integration for triggering the Function) is currently out of scope.*

> #### ```remove_notebook_callback()```
>
> This function removes try-catches around each code-block of a notebook after the notebook has been executed in Azure ML Compute so that results can be displayed cleanly in Azure DevOps. 

## ```handlers/notebook_handler.py```

This class, ```Notebook```, handles all code manipulation for notebooks to be fed to Azure ML Compute, including ```inject_code()```, ```inject_cell()```, and ```scrub_code()```.

> #### ```inject_code()```
>
> This function adds a collection of lines of code at the front or back of a collection of specified code cells.

> #### ```inject_cell()```
>
> This function adds new code cell for pre- or post-execution scripts.

> #### ```scrub_code()```
>
> This function removes all lines of code injected by inject_code from a collection of specified code cells. It also removes injected code cells from the beginning and end of the notebook.

## ```unit_testing/test_handlers.py```

This script handles all unit-testing of the Function App before it is deployed.

# Glossary

## DevOps Pipeline Variables

| Name                 	| Description                                          	| Example Value                                                     	| Where To Find                              	|
|----------------------	|------------------------------------------------------	|-------------------------------------------------------------------	|--------------------------------------------	|
| do.organization      	| DevOps Organization's Name                           	| example-organization-name                                         	| DevOps Organization's Mnemonic Name        	|
| do.project           	| DevOps Project's Name                                	| example-project-name                                              	| DevOps Project's Mnemonic Name             	|
| ex.compute           	| Azure ML Compute Target's Name                       	| example-compute                                                   	| Machine Learning Workspace's Assets        	|
| ex.image             	| Azure ML Compute's Target Image                      	| mcr.microsoft.com/azureml/base:intelmpi2018.3-ubuntu16.04         	| Azure ML SDK's RunConfig Module            	|
| fx.azureSubscription 	| Azure Subscription for Function App                  	| ExampleSubscription(a1234567-89bc-0123-def4-abc56789def)          	| Function App's Overview                    	|
| fx.name              	| Function App's Name                                  	| example-function-app                                              	| Function App's Mnemonic Name               	|
| gh.repo              	| Location of GitHub Repository                        	| https://github.com/example/repo                                   	| GitHub Repository's Overview               	|
| rp.condaFile         	| Repository's Conda File Location                     	| src/example-notebooks/environment.yml                             	| Repository's File Directory                	|
| rp.notebooks         	| Repository's Notebooks to Run                        	| one.ipynb,two.ipynb,three.ipynb                                   	| Repository's File Directory                	|
| rp.version           	| Repository's Commit/Branch of Interest               	| "bb7ad65dbc727ec09fe0613d51ce8585087de1b1", "master", "dev", etc. 	| GitHub Repository's Overview               	|
| sb.connection        	| Service Bus Queue's Connection String                	| Endpoint=sb://example.servicebus.windows.net/...                  	| Service Bus Queue's Shared Access Policies 	|
| sb.name              	| Service Bus Queue's Name                             	| example-queue-name                                                	| Service Bus Queue's Mnemonic Name          	|
| sp.client            	| Service Principal's Application (client) ID          	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def)                   	| App Registration's Overview                	|
| sp.password          	| Service Principal's Password                         	| 32 character alphanumeric string (e.g. A/fb0...)                  	| App Registration's Client Secret           	|
| sp.tenant            	| Service Principal's Directory (tenant) ID            	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def)                   	| App Registration's Overview                	|
| ws.name              	| Machine Learning Workspace's Name                    	| example-ws-name                                                   	| Workspace's Mnemonic Name                  	|
| ws.resourceGroup     	| Workspace's Resource Group's Name                    	| example-resource-group-name                                       	| Workspace's Overview                       	|
| ws.subscription      	| Machine Learning Service Workspace's Subscription ID 	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def)                   	| Workspace's Overview                       	|

# DevOps System Variables

| Name                  	| Description                	| Example Value                                   	|
|-----------------------	|----------------------------	|-------------------------------------------------	|
| system.AccessToken    	| DevOps Bearer Token        	| Long Opaque String                              	|
| system.HostType       	| DevOps Pipeline Type       	| "build"                                         	|
| system.JobId          	| DevOps Pipeline Identifier 	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def) 	|
| system.PlanId         	| DevOps Pipeline Identifier 	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def) 	|
| system.TaskInstanceId 	| DevOps Pipeline Identifier 	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def) 	|
| system.TeamProjectId  	| DevOps Pipeline Identifier 	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def) 	|

[functions-create-first-function-python]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-python
[install-azure-cli]: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
[functions-run-local]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#v2
[download-python]: https://www.python.org/downloads/
[install-azure-ml-sdk]: https://docs.microsoft.com/en-us/python/api/overview/azure/ml/install?view=azure-ml-py
[functions-triggers-bindings]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-triggers-bindings