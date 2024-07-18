---
title: "DFCX_CICD_readme"
---

This Document outlines how to use this sample code and set up the CICD
pipeline in your gcp projects.

# Primer

Using this CICD pipeline, you can

-   Promote/migrate agent across 3 GCP projects a.k.a dev -\> uat -\>
    prod

Below are the steps happens in each of the 3 projects while promoting
the agent.

**In Dev project**

-   Export agent from a designated DFCX environment from dev(coming from
    config file)

-   Automatically detects which flows are impacted based on history and
    in dev project and save it in metadata file

-   Automatically sync the flows in deployed DFCX environments once a
    flow is deployed in prod

**In UAT project**

-   Creates new versions of only those impacted flows in uat and deploy
    them to designated DFCX environment(coming from config file)

-   Run test cases relevant to impacted flows and roll back if failed in
    UAT

-   Automatically delete the previous older versions of flows in uat and
    prod once the limit is reached

-   Update the webhook apigee environment in the webhook url
    corresponding to UAT project

-   If there are multiple languages configured in the agent, it will
    automatically verify other languages pages against English language
    pages to see if agent fulfillments/response are present in every
    other languages configured.

-   Gives mechanism for UAT team to approve in UI once testing is
    completed and deploy the agent to prod post the approval

-   Automatically sync the flows in deployed DFCX environments once a
    flow is deployed in prod

**In Prod project**

-   Post UAT team approves after UAT testing, It creates new versions of
    only those impacted flows in prod and deploy them to designated DFCX
    environment(coming from config file)

-   Update the webhook apigee environment in the webhook url
    corresponding to prod project

-   Automatically delete the previous older versions of flows in uat and
    prod once the limit is reached

-   Automatically deploys the impacted flows and deploy to serving DFCX
    environment in prod

# High level Architecture

!media/image1.png

# 

# 

# Set up

## Assumptions:

1.  You have GCP account already

2.  You have created 3 separate projects for dev/uat/prod

3.  You have an agent in dev and created a dummy/empty agent in the same
    name in uat and prod project.

4.  You have a git or similar repo to source the code and to do agent
    check in to store agent artifacts whenever the build is triggered.

5.  You will create all the 3 builds in your dev project. If need be,
    you can have all the builds in a centralized project and play around
    with IAM service accounts to enable the builds to access the agent
    in dev/uat/prod projects for migration

## IAM Permissions 

1.  Create a service account and give the following IAM permissions.

-   **Dialogflow CX API Admin**

-   **Dialogflow API Client**

-   **Storage.admin and Storage Object User**

-   **CSR/Git access**

-   **Service Usage Consumer**

-   **Dialogflow \> Dialogflow Test Case Admin**

-   **Dialogflow \> Dialogflow Environment editor**

2.  Give the approver person with **cloudbuild.builds.approve** access
    in Dev project

## For the UAT and Prod builds to access UAT and PROD project to deploy the agent (See assumption no. 5), 

-   Get the service account the is used by the cloud builds in your Dev
    project

-   Go to UAT and Prod projects \> IAM role \> add principal and enter
    the service account id you got from previous step and give access to
    UAT/PROD service account as Service Usage Consumer **and**
    Dialogflow API Admin

-   Give Dev build's service account with **cloudbuild.builds.get** access

## Code Repository and Branching Strategy

This section describes the approach for setting up the repository and
branches for the agents.

**Source Repository**

Below is the reason why we need a repository

1.  Cloud Builds need to refer to some place to access the code that it
    needs to build

2.  Some Cloud Builds are set to get triggered when an agent artifact is
    checked in to the repository automatically.

3.  Maintain an audit trail to see who changed the code

4.  Maintain an audit trail to see who checked in agent artifacts in
    repo along with a commit message that explains what the change in
    agent/flow is.

## Storage Bucket

Create a gcs bucket and that will be used by the pipeline for storing
agents while exporting and restoring. Below is how the bucket structure
might look like.

!media/image2.png

## Cloud Build Configurations

There are certain configurations that have to be updated that the user
has to fill while triggering Build1 for agent promotion. Following are
the variables that will be defined for the Cloud Build.

-   **\_COMMIT_MESSAGE** - This the URL for the configuring the web-hook

### 

### Export Build:

!media/image3.png

### UAT deploy build

!media/image4.png

### Prod deploy build

!media/image5.png

## DFCX APIs

The Python Dialogflow CX Scripting [[API (DFCX
SCRAPI)]](https://github.com/GoogleCloudPlatform/dfcx-scrapi)
is a high level API that extends the official Google [[Python Client for
Dialogflow
CX]](https://github.com/googleapis/python-dialogflow-cx).
SCRAPI makes using DFCX easier, more friendly, and more pythonic for bot
builders, developers, and maintainers. This uses V3/V3beta1 endpoints
under the hood. Since it is more pythonic way of implementation,
developers will find it easy to use SCRAPI API in action.

In our CI/CD pipeline below operations are achieved using SCRAPI API

-   Find agent ID from name

-   Find flow id from name

-   [[Export the agent to
    GCS]](https://github.com/GoogleCloudPlatform/dfcx-scrapi/blob/37cf8cf7b2013a377740f68d8dcb7355632161e0/src/dfcx_scrapi/core/agents.py#L363)

-   [[Restore the
    agent]](https://github.com/GoogleCloudPlatform/dfcx-scrapi/blob/37cf8cf7b2013a377740f68d8dcb7355632161e0/src/dfcx_scrapi/core/agents.py#L438)

-   [[Cut a version of a
    flow]](https://github.com/GoogleCloudPlatform/dfcx-scrapi/blob/37cf8cf7b2013a377740f68d8dcb7355632161e0/src/dfcx_scrapi/core/versions.py#L183)

-   [[Deploy it to an
    environment]](https://github.com/GoogleCloudPlatform/dfcx-scrapi/blob/37cf8cf7b2013a377740f68d8dcb7355632161e0/src/dfcx_scrapi/core/environments.py#L359)

-   [[Run test
    cases]](https://github.com/GoogleCloudPlatform/dfcx-scrapi/blob/37cf8cf7b2013a377740f68d8dcb7355632161e0/src/dfcx_scrapi/core/test_cases.py#L410)

-   [[Compare environment
    history]](https://github.com/GoogleCloudPlatform/dfcx-scrapi/blob/37cf8cf7b2013a377740f68d8dcb7355632161e0/src/dfcx_scrapi/core/environments.py#L392)
    to find impacted flow the current instance of CI/CD builds.

## To Set up the pipeline 

1.  Setup a git or any code repository of your choice to store the code
    and agent artifacts

2.  Push the code you see in the parent folder along with this
    documentation.

3.  Make sure to update the command in the code base in
    export/repopush.sh file in line
    #7 to point to your git you have created in step 1 as this would
    check in the agent artifacts back in the same repo as your code is
    in a folder called Agent Artifacts.

4.  Use the config file as a one stop place to initiate values to
    variables that will be used throughout the pipeline. Hence this
    eases out the maintenance or reusing of the pipeline for different
    values

{

\"agent_name\" : \"carrental\",

\"dev_env_pull\" : \"ready to deploy\",

\"uat_env_deploy\" : \"ready to test\",

\"prod_env_deploy\" :\"deployed\",

\"devprodsyncenv\" :\"deployed\",

\"bucket\": \"DFCX_agent_cicd_export\",

\"dev_project\": \"yourprojectid\",

\"uat_project\" : \"yourprojectid\",

\"prod_project\": \"yourprojectid\",

\"devops_project\": \"yourprojectid\",

\"uat_webhook_env\": \"uat\",

\"prod_webhook_env\": \"prod\",

\"uat_engine_id\" :\"\",

\"prod_engine_id\" :\"\"

}



5.  Make sure the a GCP bucket is created with said structure and name
    is configured in config file

6.  Create 3 cloud builds with the configuration and name as shown in
    screenshots in the previous section and attach your repo to these
    builds.

7.  Make sure an agent is present in the same name in UAT and Prod(if it
    is first time, just create an empty agent in UAT/Prod projects)

8.  Make sure the agent in UAT and Prod projects has the environments
    created as configured in config file in fields uat_env_deploy and
    prod_env_deploy

9.  Make sure you have also created the env as you configured in config
    file devprodsyncenv in all UAT and Dev projects to sync back the
    flows after deployed in prod

## To run the Pipeline

1.  Now make some changes to your agent in Dev project and create a
    version of the flow in dfcx and deploy updated flows to the DFCX
    environment as you have configured in the config file dev_env_pull
    field.

2.  Now come to GCP Cloud build console and click on RUN on exportbuild
    in triggers section and input the commit message(basically some
    lines about your change in the agent that will be used )

3.  This will export agent and this would have done a check in in the
    repo to trigger UAT and prod builds and deployed the agent in UAT
    project.

4.  Now you can come back to cloud build console and build history tab
    and approve the build that is waiting for your approval and you can
    see that it will deploy the agent in prod post approval
    !media/image6.png

## Cavet

1.  Make sure to update the git repository name in the code base in
    export/repopush.sh file in line
    \# 7

2.  If you datastores linked to the agent, make sure to create datastore
    ids same across all three project

# Benefits

1.  Entire process of agent promotion is automated

2.  Code base is modularized according to best practices

3.  DFCX best practices are configured in the pipeline set up

4.  Same pipeline can be concurrently used for same agents by multiple
    agent developers to deploy their own flow and can be approved to
    deploy individually as we are using commit id/SHA ID as primary
    identifier across one instance of pipeline running.

5.  Datastores configurations will not break if same datastore id is
    used in all the projects
