#!/usr/bin/env python3
"""CDK app entry point for the Personalized AI Project Generator."""

import os

import aws_cdk as cdk

from stacks.generator_stack import GeneratorStack

app = cdk.App()

GeneratorStack(
    app,
    "AiProjectGeneratorStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
)

app.synth()
