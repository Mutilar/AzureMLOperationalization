# Trials and Tribulations: The State of Operationalization from an Intern's Perspective

## Introduction

I want to start by saying I am in no way an expert. But that has value. In true Monte Carlo fashion, there is value in having less experienced peoples' opinions. Nonetheless, I'll speak as though I am an authority on the matter. Feel free to call me out if I'm wrong though!

I've only recently been exposed to the full Azure suite of tools and applications. And there are quite a few. For example, if you want a way to agentless execute a small amount of code, there are many options:

    Azure WebJobs 
    Azure Functions
    Azure Event Hub
 
Which was daunting, because my intern project required me to execute what I thought at the time were small amounts of code.

There isn't a cohesive story being told with Azure. It feels disjointed. And that has implications not only on a UI/UX level, but in an engineering level as well.

## The SDK

The AzureML SDK is a monstrous thing. But it makes sense from a customer-facing perspective. A data scientist using the SDK can easily and intuitively run notebooks locally while tapping into the Azure cloud in a user-friendly manner. However, data scientists aren't really our customers, per say. Data scientists aren't focused on operationalizing their workflows. That's a DevOps perspective.

If a data-scientist can spent hours playing ping-pong while "notebooks are running" on their machine, that's in their best interest.

So, attempting to operationalize a system with tools designed with no dedicated intent to do so leads to some... inefficiencies.

## Azure Functions

Azure HTTP requests require a response in 20 seconds. That seems pretty reasonable for most cases. But one of the main hurdles I faced early on was in "cold-starts" of my Azure function with the Azure ML SDK. The aforementioned SDK is quite large (around 500 MB unzipped). This caused a cold-start time of between 45-65 seconds. Thus, an HTTP-based function was essentially impossible with the 20 second timeout limitation. 

I did find a work-around to this, using two seperate Azure Function Applications, the first being light-weight and immediately responding back with an "OK" while spinning up a separate thread to call the larger Azure Function App-- all this to get around an arbitrary timeout limitation.

Some external Azure customers found other work-arounds:

https://mikhail.io/2018/04/azure-functions-cold-starts-in-numbers/
https://mikhail.io/2018/05/azure-functions-cold-starts-beyond-first-load/

The solution? Call the function every 10 minutes to prevent it from needing to cold-start. That's like keeping your car idling in your garage to avoid the hassle of turning the key to turn it on when you need to drive to work.

Clearly this just wasn't an expected/appriopriate application.

But I realized, this is a restraint on HTTP, not the function. So, switching to a Service Bus/Event Grid solution did the trick, crisis averted. 

## Polling is ubiquitous

wait_for_completion


