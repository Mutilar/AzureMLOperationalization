
# Azure ML Operationalization

[![Build Status](https://dev.azure.com/t-brhung/brhung-test-pipeline/_apis/build/status/Mutilar.brhung-deployment-testing?branchName=master)](https://dev.azure.com/t-brhung/brhung-test-pipeline/_build/latest?definitionId=8&branchName=master)

Streamlining and expediating a data scientist's CI/CD workflow leveraging prebaked functionalities of Azure DevOps Pipelines, Azure Functions, and Azure Service Bus Queues.

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
> > > - ```file_handler.py```
> > > - ```request_handler.py```
> > - tests
> > > - ```test_handlers.py```
> > - ```azure-pipelines.yml```
> > - ```requirements.txt``` 

## ```azure-pipelines.yml```

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
>     - task: PublishToAzureServiceBus@1
> ```
> 


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

## ```function.json```

This file specifies the location of main function (e.g. ```__init__.py```), as well as the Service Bus binding for the application.

## ```__init__.py```

This script holds all the pythonic logic of the application. The main function is short, favoring a helper function to handle the ```start_build_pipeline()```. 

> #### ```start_build_pipeline()```
> 
> Fetches the repository of interest, creates a new Experiment SDK Object, and submits a set of notebook Runs to that object. 

## ```azureml_handler.py```

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

## ```file_handler.py```

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

## ```request_handler.py```

This script handles all HTTP related tasks, including ```post_new_run()``` and ```post_run_results()```.

> #### ```post_new_run()```
>
> This function, along with its helper functions, [creates a new DevOps Test Run](https://docs.microsoft.com/en-us/rest/api/azure/devops/test/runs/create?view=azure-devops-rest-5.0) via the DevOps API.

> #### ```post_run_results()```
>
> This function, along with its helper functions, [updates a DevOps Test Run](https://docs.microsoft.com/en-us/rest/api/azure/devops/test/results/add?view=azure-devops-rest-5.0) with result telemetry via the DevOps API.

## ```test_handlers.py```

This script handles all unit-testing of the Function App before it is deployed. Currently, unit tests only cover ```file_handler.py```-specific functions, as all other functions are very primitive. 

# Glossary

## DevOps Pipeline Variables

| Name            	| Description                                          	| Example Value                                    	| Where To Find                              	|
|-----------------	|------------------------------------------------------	|--------------------------------------------------	|--------------------------------------------	|
| sb.connection   	| Service Bus Queue's Connection String                	| Endpoint=sb://example.servicebus.windows.net/... 	| Service Bus Queue's Shared Access Policies 	|
| sb.name         	| Service Bus Queue's Name                             	| example-queue-name                               	| Service Bus Queue's Mnemonic Name          	|
| sp.password     	| Service Principal's Password                         	| 32 character alphanumeric string (e.g. A/fb0...) 	| App Registration's Client Secret           	|
| sp.client       	| Service Principal's Application (client) ID          	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def)  	| App Registration's Overview                	|
| sp.tenant       	| Service Principal's Directory (tenant) ID            	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def)  	| App Registration's Overview                	|
| ws.subscription 	| Machine Learning Service Workspace's Subscription ID 	| GUID (e.g. a1234567-89bc-0123-def4-abc56789def)  	| Workspace's Overview                       	|

[functions-create-first-function-python]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-python
[install-azure-cli]: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
[functions-run-local]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#v2
[download-python]: https://www.python.org/downloads/
[install-azure-ml-sdk]: https://docs.microsoft.com/en-us/python/api/overview/azure/ml/install?view=azure-ml-py
[functions-triggers-bindings]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-triggers-bindings