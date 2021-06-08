<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/othneildrew/Best-README-Template">
    <img src="images/logo.png" alt="Scrappy, the SAPI mascot!" width="200">
  </a>

  <h3 align="center">Python Dialogflow CX Scripting API (SAPI)</h3>

  <p align="center">
    A high level scripting API for bot builders, developers, and maintainers.</br>
    <a href="https://screencast.googleplex.com/cast/NjQ4MTA4Nzc4ODIyMDQxNnwzODc1MzY1Zi0yNA">Generic Demo</a>
    ·
    <a href="https://screencast.googleplex.com/cast/NTkxMjYxNDUzMjAyMjI3MnxlOGU0ZWNhNi01NQ">Copy/Paste Agent Resources Demo</a>
    <!-- ·
    <a href="https://github.com/othneildrew/Best-README-Template/issues">Request Feature</a> -->
    <br/>

    
  </p>
</p>

<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#introduction">Introduction</a>
      <ul>
        <li><a href="#what-can-i-do-with-dfcx-sapi">What Can I Do with SAPI?</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a>
      <ul>
        <li><a href="#library-composition">Library Composition</a></li>
      </ul>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>

<!-- INTRODUCTION -->
# Introduction

The Python Dialogflow CX Scripting API (DFCX SAPI) is a high level API that extends the official Google [Python Client for Dialogflow CX](https://github.com/googleapis/python-dialogflow-cx) which makes using CX easier, more friendly, and more pythonic for bot builders, developers and maintainers.

```
SAPI --> Python Dialogflow CX
as
Keras --> Tensorflow
```

## What Can I Do With DFCX SAPI?
With DFCX SAPI, you can perform many bot building and maintenance actions at scale including, but not limited to:
- Create, Update, Delete, Get, List for all CX resources types (i.e. Intents, Entity Types, Pages, Flows, etc.)
- Convert commonly accessed CX Resources to Pandas Dataframes for data manipulation and analysis
  - Ex: `bulk_intents_to_dataframe` provides you all intents and training phrases in a Pandas DataFrame that can be manipulated and/or exported to CSV or back to CX
- Have fully automated conversations with a CX agent (powerful for regression testing!)
- Extract Validation information to assist in tuning your agent NLU, routes, etc.
- Extract Change History information to assist with Change Management and Accountability for your devlepment team
- Search Util functions to look across all Flows/Pages/Routes to find a specific parameter or utterance you need to locate
- Copy Util functions that allow you to quickly move CX resource between agents!
  - Ex: `copy_intent_to_agent` allows you to choose source and destination Agent IDs and a human readable Intent Display Name and `BAM!` Intent is moved with all training phrases to the destination agent!
- Maker/Builder Util functions that allow you to build the fundamental protobuf objects that CX uses for each resource type
  - Ex: if you want to build a new Intent (or hundreds!) with training phrases from a pandas dataframe, you can build them all offline/in memory using the build_intent method
- ...and much, much more!

## Built With
* Python 3.8+

<!-- GETTING STARTED -->
# Getting Started
## Prerequisites
- Install Requirements  
`pip install -r requirements.txt`

- Authentication  
In order to use the functions and API calls to Dialogflow CX, you will need a Service Account that has appropriate access to your GCP project.  
For more information on view the official docs for [Creating and Managing GCP Service Accounts](https://cloud.google.com/iam/docs/creating-managing-service-accounts).

## Installation
1. Set up your GCP Service Account
2. Clone the repo  
`git clone git@gitlab.com:google-pso/ais/verizon/dfcx_sapi.git`

<!-- USAGE EXAMPLES -->
# Usage
To run a simple bit of code you can do the following:
- Import a Class from `dfcx_sapi.core`
- Assign your Service Account to a local variable

```python
from dfcx_sapi.core.intents import Intents

creds_path = '<PATH_TO_YOUR_SERVICE_ACCOUNT_JSON_FILE>'
agent_path = '<FULL_DFCX_AGENT_ID_PATH>'

# DFCX Agent ID paths are in this format:
# 'projects/<project_id>/locations/<location_id>/agents/<agent_id>'

# Instantiate your class object and pass in your credentials
i = Intents(creds_path)

# Retrieve all Intents and Training Phrases from an Agent and push to a Pandas DataFrame
df_intents = i.list_intents(agent_path)
```

_For more examples, please refer to [Examples](examples/) or [Tools](tools/)._

# Library Composition
A brief overview of the motivation behind the library structure

## Core  
The [Core](core/) folder is synonymous with the core Resource types in the DFCX Agents like:
- agents
- intents
- entity_types
- etc.

The [Core](core/) folder is meant to contain the fundamental building blocks for even higher level customized tools and applications that can be built with this library.

## Tools
The [Tools](tools/) folder contains various customized toolkits that allow you to do more complex bot management tasks.
These include things like:
- Manipulating Agent Resource types into various DataFrame structure for data scienc-y type tasks
- Copying Agent Resources between Agents and GCP Projects on a resource by resource level
- Moving data to and from DFCX and other GCP Services like BigQuery, Sheets, etc.
- Creating customized search queries inside of your agent resources
  - i.e. - Find all parameters in all pages in the agent that contain the string `dtmf`

<!-- ROADMAP -->
# Roadmap
TBD

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
Henry Drescher - drescher@google.com  

Project Link: [go/dfcx-sapi](go/dfcx-sapi)

<!-- ACKNOWLEDGEMENTS -->
# Acknowledgements
[Dialogflow CX Python Client Library](https://github.com/googleapis/python-dialogflow-cx)



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->