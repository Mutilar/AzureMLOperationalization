
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

This file controls the CD pipeline for the Function App.

```yml
jobs:
- job:
  displayName: Deploy Job
  pool: 
    vmImage: 'ubuntu-16.04'
  steps:
  # Set Python Version
  - task: UsePythonVersion@0
    displayName: Setting Required Python Version for Azure Functions
    inputs:
      versionSpec: '3.6'
      architecture: 'x64'
  # INIT CONDA ENVIRONMENT
  - bash: |
      python3.6 -m venv worker_venv
      source worker_venv/bin/activate
      pip3.6 install setuptools
      pip3.6 install -r requirements.txt
    displayName: Install Dependencies
  # UNIT TESTS
  - bash: |
      source worker_venv/bin/activate
      pytest
    displayName: Run Unit Tests
  # BUNDLE FUNCTION
  - task: ArchiveFiles@2
    inputs:
      rootFolderOrFile: '$(System.DefaultWorkingDirectory)/'
      includeRootFolder: false
      archiveType: 'zip'
      archiveFile: '$(System.DefaultWorkingDirectory)/output.zip'
      replaceExistingArchive: true
  # DEPLOY FUNCTION
  - task: AzureFunctionApp@1
    inputs:
      azureSubscription: 'ExperimentnLearnNonProd(bc69d98c-7d2b-4542-88a4-f86eb4aea4a5)'
      appType: 'functionAppLinux'
      appName: 'brhung-deployment-test'
      package: '$(System.DefaultWorkingDirectory)/output.zip'
- job:
  displayName: E2E Test
  pool: server
  steps:
  # E2E Testing
  - task: PublishToAzureServiceBus@1
    inputs:
      azureSubscription: 'serviceBusConnectionString' # Defined in DevOps Project Settings -> Service Connections
      messageBody: >
        {
          ... (see CI pipeline definition for more details) ...
        }
      waitForCompletion: true # Allows for POST callback to close pipeline 
```

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