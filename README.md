
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
> > - RunNotebookServiceBus
> > > - ```__init__.py```
> > > - ```function.json```
> > - Handlers
> > > - ```azureml_handler.py```
> > > - ```file_handler.py```
> > - ```azure-pipelines.yml```
> > - ```requirements.txt``` 

## ```azure-pipelines.yml```

This file controls the CD pipeline for the Function App. It functions with two main stages: 

### ```Deployment```

```yml
- stage: Deployment
  jobs:
  - job: 
    pool:
      vmImage: 'ubuntu-16.04'
    steps:
    - task: UsePythonVersion@0
    - bash: pip3.6 install -r requirements.txt
    - bash: pytest
    - task: ArchiveFiles@2
    - task: AzureFunctionApp@1
```

This agent-based stage prepares the deployment environment, unit-tests, bundles, and finally deploys the Azure Function Application. 

### ```Validation```

```yml
- stage: Validation
  jobs:
  - job: 
    pool: server
    steps:
    - task: PublishToAzureServiceBus@1
```

This agentless stage then validates the changes by running a controlled job through the new deployment of the application to ensure everything is functioning as expected.

## ```requirements.txt```

This file controls the dependencies required for the Azure Function. This is mainly the Azure ML SDK, its associated dependencies, and support for HTTP requests, file system manipulation, etc.

```
...
azureml==0.2.7
azureml-contrib-notebook==1.0.43.*
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

This file controls where the app looks for a main function (in this case, ```__init__.py```), as well as the bindings for the app. We can see below what the binding for a Service Bus Queue looks like:

```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "msg",
      "type": "serviceBusTrigger",
      "direction": "in",
      "queueName": "function-queue",
      "connection": "serviceBusConnectionString"
    }
  ]
}
```

## ```__init__.py```

This script holds all the pythonic logic of the application. The main function is short, favoring a helper function to handle the ```kick_off()```. 

### ```kick_off()```

Kick-off fetches the repository of interest, and submits a new notebook run for each notebook specified in the input parameters.

## ```azureml_handler.py```

### ```fetch_experiment```

### ```fetch_run_configuration```

### ```submit_run```

## ```file_handler.py```

### ```fetch_repository```



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

# Relevant Documentation

- [Creating your first python function][functions-create-first-function-python]
- [Installing the Azure CLI][install-azure-cli]
- [Installing the Azure ML SDK][install-azure-ml-sdk]

[functions-create-first-function-python]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-python
[install-azure-cli]: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
[functions-run-local]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#v2
[download-python]: https://www.python.org/downloads/
[install-azure-ml-sdk]: https://docs.microsoft.com/en-us/python/api/overview/azure/ml/install?view=azure-ml-py
[functions-triggers-bindings]: https://docs.microsoft.com/en-us/azure/azure-functions/functions-triggers-bindings