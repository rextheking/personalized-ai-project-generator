"""The main CDK stack for the Personalized AI Project Generator.

Provisions:
- Lambda running the Strands agent
- API Gateway HTTP API with a /generate route
- S3 bucket for the static web frontend (private, served via CloudFront)
- CloudFront distribution in front of the web bucket

The Lambda dependencies are bundled locally with pip targeting Linux wheels, so
no Docker daemon or SAM CLI is required to deploy.
"""

import subprocess
import sys
from pathlib import Path

import jsii
from aws_cdk import (
    BundlingOptions,
    BundlingOutput,
    CfnOutput,
    DockerImage,
    Duration,
    ILocalBundling,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct

# Path to the backend code, relative to the infra directory where cdk runs.
_BACKEND_CODE_PATH = "../backend"

# Claude Sonnet 4 cross-region inference profile in us-east-1.
_DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"


@jsii.implements(ILocalBundling)
class _LocalPipBundling:
    """Bundle the Lambda locally with pip instead of Docker.

    Keeps deploys fast and removes the Docker prerequisite. Installs the
    dependencies as Linux x86_64 wheels and copies the agent source alongside
    them.
    """

    def try_bundle(self, output_dir: str, options) -> bool:
        src = Path(_BACKEND_CODE_PATH).resolve()
        pip_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--no-cache-dir",
            "--index-url",
            "https://pypi.org/simple/",
            "-r",
            str(src / "requirements.txt"),
            "-t",
            output_dir,
            "--platform",
            "manylinux2014_x86_64",
            "--implementation",
            "cp",
            "--python-version",
            "3.12",
            "--only-binary=:all:",
            "--upgrade",
        ]
        try:
            subprocess.check_call(pip_cmd)
            # Copy the handler and the agent package next to the dependencies.
            subprocess.check_call(["cp", str(src / "app.py"), output_dir])
            subprocess.check_call(["cp", "-r", str(src / "agent"), output_dir])
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"Local bundling failed: {exc}")
            return False
        return True


class GeneratorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Lambda running the Strands agent ---
        agent_lambda = _lambda.Function(
            self,
            "AgentLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.X86_64,
            handler="app.handler",
            code=_lambda.Code.from_asset(
                _BACKEND_CODE_PATH,
                bundling=BundlingOptions(
                    image=DockerImage.from_registry(
                        "public.ecr.aws/sam/build-python3.12"
                    ),
                    local=_LocalPipBundling(),
                    command=[
                        "bash",
                        "-c",
                        "pip install --no-cache-dir -r requirements.txt "
                        "-t /asset-output && cp app.py /asset-output/ "
                        "&& cp -r agent /asset-output/",
                    ],
                    platform="linux/amd64",
                    output_type=BundlingOutput.AUTO_DISCOVER,
                ),
            ),
            memory_size=512,
            timeout=Duration.seconds(60),
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "BEDROCK_MODEL_ID": _DEFAULT_MODEL_ID,
                "ALLOWED_ORIGIN": "*",
            },
        )

        # Least privilege: the agent only needs to invoke Bedrock models. The
        # inference profile fans out to regional foundation models, so allow
        # both the profile and the underlying model ARNs.
        agent_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/*",
                    "arn:aws:bedrock:*::foundation-model/*",
                ],
            )
        )

        # --- HTTP API ---
        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_headers=["Content-Type"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_origins=["*"],
                max_age=Duration.days(1),
            ),
        )

        http_api.add_routes(
            path="/generate",
            methods=[apigwv2.HttpMethod.POST],
            integration=apigwv2_integrations.HttpLambdaIntegration(
                "LambdaIntegration", agent_lambda
            ),
        )

        # --- Static web frontend bucket ---
        web_bucket = s3.Bucket(
            self,
            "WebBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # --- CloudFront distribution ---
        distribution = cloudfront.Distribution(
            self,
            "WebDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.S3BucketOrigin.with_origin_access_control(
                    web_bucket
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(10),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(10),
                ),
            ],
            comment="Personalized AI Project Generator web distribution",
        )

        # --- Outputs ---
        CfnOutput(
            self,
            "ApiEndpoint",
            value=f"{http_api.api_endpoint}/generate",
            description="POST your prompt here. Goes into web/config.js.",
        )
        CfnOutput(
            self,
            "WebsiteURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="The public site URL.",
        )
        CfnOutput(
            self, "WebBucketName", value=web_bucket.bucket_name
        )
        CfnOutput(
            self, "DistributionId", value=distribution.distribution_id
        )
