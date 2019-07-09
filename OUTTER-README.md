## ```azure-pipelines.yml```

This file controls the DevOps pipeline flow. The pipeline required for this project is very simple. The first snippet seen below defines the [server job](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/phases?tabs=yaml&view=azure-devops#server-jobs):

```yml
jobs:
- job: test 
  timeoutInMinutes: 10 # Defining Max Runtime
  pool: server # Defining Server Job
```
Then, the only step in the pipeline is to publish the Azure ML Compute run parameters to a Service Bus Queue that will trigger the Azure Function to package and send the request:

```yml
  # Kick Off:
  steps:
  - task: PublishToAzureServiceBus@1
    inputs:
      azureSubscription: 'test' # Defined in DevOps Project Settings -> Service Connections
      messageBody: '{"job":"kick_off", ...}' # See azure-pipeline-paramters.json
      waitForCompletion: true # Allows for POST callback to close pipeline
```