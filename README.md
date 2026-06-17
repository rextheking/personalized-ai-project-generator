# Personalized AI Project Generator

An AI advisor that turns your AWS background into hands-on project ideas, then
hands you a step by step build plan for the one you pick. The reasoning runs on
an agent built with the [Strands Agents SDK](https://strandsagents.com) and
Amazon Bedrock. The whole thing ships as a web app you can deploy to AWS and
share with anyone.

This is the practical follow on to the Amazon Q Developer CLI project generator.
Same idea, different engine. Instead of prompting a CLI, you build the advisor
yourself as a real agent and put a browser front end on it.

## What you get

- A Strands agent with two custom tools, one that suggests tailored projects and
  one that returns a build plan
- A Lambda backend behind an HTTP API
- A static frontend on S3 served through CloudFront
- One deploy script that stands the whole stack up

## Architecture

```
Browser (S3 + CloudFront)
        |
        |  POST /generate  { "prompt": "..." }
        v
API Gateway (HTTP API)
        |
        v
Lambda  -->  Strands Agent  -->  custom tools (project ideas, build plans)
                  |
                  v
            Amazon Bedrock (Claude)
```

## Repository layout

```
personalized-ai-project-generator/
├── backend/
│   ├── agent/
│   │   ├── generator.py   # builds the Strands agent
│   │   ├── tools.py       # the @tool functions
│   │   └── prompts.py     # the system prompt
│   ├── app.py             # Lambda handler for API Gateway
│   ├── local_run.py       # run the agent in your terminal
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── infrastructure/
│   ├── app.py             # CDK app entry point
│   ├── cdk.json           # CDK config
│   ├── requirements.txt   # CDK Python deps
│   ├── Makefile           # install, bootstrap, deploy, upload-web
│   └── stacks/
│       └── generator_stack.py  # Lambda, HTTP API, S3, CloudFront
```

## Prerequisites

- An AWS account with permissions for Lambda, API Gateway, S3, CloudFront and
  IAM
- [Amazon Bedrock model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
  enabled for Claude in your region
- Python 3.12
- Node.js and the [AWS CDK CLI](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
  (`npm install -g aws-cdk`)
- The [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html),
  configured with your credentials

The Lambda dependencies are bundled locally with pip, so you do not need Docker
or the SAM CLI to deploy.

## Run the agent locally first

Before deploying anything, see the agent work on your machine.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python local_run.py
```

Then try a prompt:

```
I am an AWS Certified Cloud Practitioner. Suggest 3 beginner serverless
projects I can finish in an afternoon.
```

Ask a follow up to get a plan:

```
Give me a build plan for the serverless REST API project.
```

## Deploy to AWS

The infrastructure is defined with AWS CDK. A Makefile wraps the common steps.

```bash
cd infrastructure
make install      # create venv and install CDK deps
make bootstrap    # first time only, per account/region
make deploy       # provision Lambda, API Gateway, S3 and CloudFront
make upload-web   # write config.js, upload the frontend, invalidate the cache
```

`make deploy` prints the stack outputs, including the website URL and the API
endpoint. `make upload-web` reads those outputs, points the frontend at the live
API and pushes it to S3. The first CloudFront deploy takes a few minutes to
propagate.

To see the outputs again later:

```bash
make outputs
```

To tear everything down:

```bash
make destroy
```

## How the agent is built

The agent lives in `backend/agent/generator.py`. It uses a `BedrockModel`, a
system prompt that frames it as an AWS project advisor and two custom tools.

```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")
agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[generate_project_ideas, build_implementation_plan],
)
```

The tools in `backend/agent/tools.py` use the `@tool` decorator. The model reads
each function's docstring and type hints to decide when to call it.

## Security notes

- The Lambda role only allows `bedrock:InvokeModel`. Nothing else.
- The S3 bucket blocks all public access. CloudFront reads it through an Origin
  Access Control, so the bucket is never exposed directly.
- CORS is open (`*`) by default to keep first deploys simple. Lock
  `ALLOWED_ORIGIN` down to your CloudFront domain for anything beyond a demo.
- There is no auth on the API. Add API keys, usage plans or Cognito before you
  put it in front of real traffic, since every call costs Bedrock tokens.

## Cleaning up

```bash
cd infrastructure
make destroy
```

This removes the Lambda, API, bucket and CloudFront distribution. The S3 bucket
is set to auto-delete its objects, so the teardown is clean. CloudFront takes a
little while to fully delete in the background, which is normal.

## Where to take it next

- Add a tool that scores a finished project against the Well-Architected pillars
- Stream responses to the browser instead of waiting for the full reply
- Generate a CDK or SAM template for whichever project the user picks

## Built on

- [Strands Agents SDK](https://strandsagents.com)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [AWS CDK](https://aws.amazon.com/cdk/)
