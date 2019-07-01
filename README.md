
service bus connection string
azure service bus
https://dev.azure.com/t-brhung/brhung-test-pipeline/_settings/adminservices?resourceId=968b01fc-1825-43f5-85da-abd1b55034d7&_a=resources&resource=%5Bobject%20Object%5D

for

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




enable function ==> function -> "configuration" (application settings) -> new application setting