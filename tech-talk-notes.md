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

