<!-- PROJECT LOGO -->
<div align="center">
    <img src="images/logo.png" alt="Scrappy, the SCRAPI mascot!" width="200">

  <h3 align="center">Python Dialogflow CX Scripting API (SCRAPI)</h3>
  <p align="center">
    A high level scripting API for bot builders, developers, and maintainers.<br>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#introduction">Introduction</a>
      <ul>
        <li><a href="#what-can-i-do-with-dfcx-scrapi">What Can I Do with SCRAPI?</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#environment-setup">Environment Setup</a></li>
        <li><a href="#authentication">Authentication</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a>
    <li>
      <a href="#library-composition">Library Composition</a>
      <ul>
        <li><a href="#core">Core</a></li>
        <li><a href="#tools">Tools</a></li>
      </ul>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>

<!-- INTRODUCTION -->
# Introduction

The Python Dialogflow CX Scripting API (DFCX SCRAPI) is a high level API that extends the official Google [Python Client for Dialogflow CX](https://github.com/googleapis/python-dialogflow-cx). SCRAPI makes using DFCX easier, more friendly, and more pythonic for bot builders, developers, and maintainers.

```
SCRAPI --> Python Dialogflow CX
as
Keras --> Tensorflow
```

## What Can I Do With DFCX SCRAPI?
With DFCX SCRAPI you can perform many bot building and maintenance actions at scale including, but not limited to:
- Create, Update, Delete, Get, and List for all CX resources types (i.e. Intents, Entity Types, Pages, Flows, etc.)
- Convert commonly accessed CX Resources to Pandas Dataframes
- Have fully automated conversations with a CX agent (powerful for regression testing!)
- Extract Validation information
- Extract Change History information
- Search across all Flows/Pages/Routes to find a specific parameter or utterance using Search Util functions
- Quickly move CX resources between agents using Copy Util functions!
- Build the fundamental protobuf objects that CX uses for each resource type using Maker/Builder Util functions
- ...and much, much more!

## Built With
* Python 3.8+

<!-- GETTING STARTED -->
# Getting Started
## Environment Setup
Set up Google Cloud Platform credentials and install dependencies.
```sh
gcloud auth login
gcloud auth application-default login
gcloud config set project <project name>
```
```sh
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Authentication  
In order to use the functions and API calls to Dialogflow CX, you will need a Service Account that has appropriate access to your GCP project.  
For more information and to view the official documentation for service accounts go to [Creating and Managing GCP Service Accounts](https://cloud.google.com/iam/docs/creating-managing-service-accounts).

<!-- USAGE EXAMPLES -->
# Usage
To run a simple bit of code you can do the following:
- Import a Class from `dfcx_scrapi.core`
- Assign your Service Account to a local variable

```python
from dfcx_scrapi.core.intents import Intents

creds_path = '<PATH_TO_YOUR_SERVICE_ACCOUNT_JSON_FILE>'
agent_path = '<FULL_DFCX_AGENT_ID_PATH>'

# DFCX Agent ID paths are in this format:
# 'projects/<project_id>/locations/<location_id>/agents/<agent_id>'

# Instantiate your class object and pass in your credentials
i = Intents(creds_path, agent_id=agent_path)

# Retrieve all Intents and Training Phrases from an Agent and push to a Pandas DataFrame
df = i.bulk_intent_to_df()
```

_For more examples, please refer to [Examples](/examples) or [Tools](/src/dfcx_scrapi/tools)._

# Library Composition
Here is a brief overview of the SCRAPI library's structure and the motivation behind that structure.

## Core  
The [Core](/src/dfcx_scrapi/core) folder is synonymous with the core Resource types in the DFCX Agents like:
- agents
- intents
- entity_types
- etc.

The [Core](/src/dfcx_scrapi/core) folder is meant to contain the fundamental building blocks for even higher level customized tools and applications that can be built with this library.

## Tools
The [Tools](/src/dfcx_scrapi/tools) folder contains various customized toolkits that allow you to do more complex bot management tasks, such as
- Manipulate Agent Resource types into various DataFrame structures
- Copy Agent Resources between Agents and GCP Projects on a resource by resource level
- Move data to and from DFCX and other GCP Services like BigQuery, Sheets, etc.
- Create customized search queries inside of your agent resources

<!-- CONTRIBUTING -->
# Contributing
We welcome any contributions or feature requests you would like to submit!

1. Fork the Project
2. Create your Feature Branch (git checkout -b feature/AmazingFeature)
3. Commit your Changes (git commit -m 'Add some AmazingFeature')
4. Push to the Branch (git push origin feature/AmazingFeature)
5. Open a Pull Request

<!-- LICENSE -->
# License
Distributed under the Apache 2.0 License. See [LICENSE](LICENSE.txt) for more information.

<!-- CONTACT -->
# Contact
Patrick Marlow - pmarlow@google.com  - [@kmaphoenix](https://github.com/kmaphoenix)  
David "DC" Collier - dcollier@google.com  - [@DCsan](https://github.com/dcsan)  
Henry Drescher - drescher@google.com  - [@Hgithubacct](https://github.com/Hgithubacct)  

Project Link: [https://github.com/GoogleCloudPlatform/dfcx-scrapi](https://github.com/GoogleCloudPlatform/dfcx-scrapi)

<!-- ACKNOWLEDGEMENTS -->
# Acknowledgements
[Dialogflow CX Python Client Library](https://github.com/googleapis/python-dialogflow-cx)   
[Hugging Face - Pegasus Paraphrase](https://huggingface.co/tuner007/pegasus_paraphrase)



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
