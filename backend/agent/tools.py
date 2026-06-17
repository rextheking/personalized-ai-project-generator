"""Custom Strands tools for the Personalized AI Project Generator.

These tools give the agent structured building blocks. The model still does the
reasoning and the writing, but the tools keep project metadata consistent and
grounded so the agent does not invent services or wildly wrong time estimates.
"""

from strands import tool


# A small, curated catalog the agent can draw from. Keeping this in code means
# every suggestion is anchored to a real service combination with a sane time
# estimate, while the model handles the personalized explanation.
PROJECT_CATALOG = [
    {
        "title": "Static portfolio website on S3 and CloudFront",
        "level": "beginner",
        "services": ["Amazon S3", "Amazon CloudFront", "Amazon Route 53"],
        "themes": ["web hosting", "storage", "content delivery"],
        "hours": "2-3",
        "outcomes": [
            "Host static content in an S3 bucket",
            "Serve it through a CloudFront distribution",
            "Understand origin access and cache behavior",
        ],
        "real_world": "Personal portfolio, landing page or documentation site.",
    },
    {
        "title": "Serverless contact form with Lambda and API Gateway",
        "level": "beginner",
        "services": ["AWS Lambda", "Amazon API Gateway", "Amazon SES"],
        "themes": ["serverless", "api", "automation"],
        "hours": "3-4",
        "outcomes": [
            "Build an HTTP API with API Gateway",
            "Process requests in a Lambda function",
            "Send email through Amazon SES",
        ],
        "real_world": "Contact or feedback form for any website without a server.",
    },
    {
        "title": "Image thumbnail pipeline with S3 events and Lambda",
        "level": "intermediate",
        "services": ["Amazon S3", "AWS Lambda", "Amazon CloudWatch"],
        "themes": ["serverless", "event-driven", "storage", "automation"],
        "hours": "3-5",
        "outcomes": [
            "Trigger Lambda from S3 upload events",
            "Process images and write results back to S3",
            "Read logs and metrics in CloudWatch",
        ],
        "real_world": "Automatic thumbnail or watermark generation for an app.",
    },
    {
        "title": "Serverless REST API with DynamoDB",
        "level": "intermediate",
        "services": ["Amazon API Gateway", "AWS Lambda", "Amazon DynamoDB"],
        "themes": ["serverless", "api", "database", "nosql"],
        "hours": "4-6",
        "outcomes": [
            "Model data in a DynamoDB table",
            "Build CRUD endpoints with Lambda and API Gateway",
            "Apply least-privilege IAM roles per function",
        ],
        "real_world": "Backend for a todo app, notes app or simple catalog.",
    },
    {
        "title": "AI chat assistant with Amazon Bedrock and Lambda",
        "level": "intermediate",
        "services": ["Amazon Bedrock", "AWS Lambda", "Amazon API Gateway"],
        "themes": ["ai", "serverless", "api", "genai"],
        "hours": "4-6",
        "outcomes": [
            "Invoke a foundation model through Amazon Bedrock",
            "Expose the model behind an API",
            "Handle prompts and responses safely",
        ],
        "real_world": "Support bot, writing helper or Q&A widget on a site.",
    },
    {
        "title": "Containerized app on ECS Fargate behind a load balancer",
        "level": "advanced",
        "services": [
            "Amazon ECS",
            "AWS Fargate",
            "Elastic Load Balancing",
            "Amazon ECR",
        ],
        "themes": ["containers", "networking", "scaling"],
        "hours": "6-8",
        "outcomes": [
            "Push a container image to Amazon ECR",
            "Run it on ECS Fargate with no servers to manage",
            "Route traffic through an Application Load Balancer",
        ],
        "real_world": "Production style hosting for a web service or API.",
    },
    {
        "title": "Event-driven order processor with EventBridge and SQS",
        "level": "advanced",
        "services": [
            "Amazon EventBridge",
            "Amazon SQS",
            "AWS Lambda",
            "Amazon DynamoDB",
        ],
        "themes": ["event-driven", "serverless", "messaging", "decoupling"],
        "hours": "6-8",
        "outcomes": [
            "Route events with EventBridge rules",
            "Buffer work in an SQS queue",
            "Process messages and persist state in DynamoDB",
        ],
        "real_world": "Order, payment or notification pipeline that scales.",
    },
]


def _matches(project: dict, level: str, interests: list[str]) -> bool:
    """Return True if a catalog project fits the requested level and interests."""
    if level and project["level"] != level.lower().strip():
        return False
    if not interests:
        return True
    haystack = " ".join(
        project["themes"] + [s.lower() for s in project["services"]]
    ).lower()
    return any(term.lower().strip() in haystack for term in interests if term.strip())


@tool
def generate_project_ideas(
    skill_level: str,
    interests: str = "",
    max_results: int = 3,
) -> dict:
    """Suggest AWS project ideas tailored to a person's skill level and interests.

    Args:
        skill_level: One of "beginner", "intermediate" or "advanced".
        interests: Comma separated topics or services, for example
            "serverless, api, dynamodb" or "ai, storage".
        max_results: Maximum number of project ideas to return.

    Returns:
        A dictionary with a list of matching projects, each including the AWS
        services involved, learning outcomes, an estimated time to complete and
        a real-world application.
    """
    interest_list = [i for i in interests.split(",")] if interests else []

    matches = [
        p for p in PROJECT_CATALOG if _matches(p, skill_level, interest_list)
    ]

    # Fall back to level-only matches if interests filtered everything out, so
    # the user always gets something useful.
    if not matches:
        matches = [
            p
            for p in PROJECT_CATALOG
            if not skill_level or p["level"] == skill_level.lower().strip()
        ]
    if not matches:
        matches = PROJECT_CATALOG

    selected = matches[: max(1, max_results)]

    return {
        "skill_level": skill_level,
        "interests": interest_list,
        "count": len(selected),
        "projects": selected,
    }


@tool
def build_implementation_plan(project_title: str) -> dict:
    """Return a step by step build plan for a known project.

    Args:
        project_title: The title of a project from a previous suggestion. A
            partial title also works, the closest match is used.

    Returns:
        A dictionary with the matched project and an ordered list of build
        steps. Each step has a goal, the kind of action involved and the
        security or best-practice note to keep in mind.
    """
    title_lower = project_title.lower().strip()
    project = next(
        (
            p
            for p in PROJECT_CATALOG
            if title_lower in p["title"].lower() or p["title"].lower() in title_lower
        ),
        None,
    )

    if project is None:
        return {
            "found": False,
            "message": (
                f"No catalog project matched '{project_title}'. Ask for project "
                "ideas first, then request a plan using one of those titles."
            ),
        }

    # A generic, safe scaffold for the build plan. The agent expands each step
    # into concrete CLI commands and explanations for the specific services.
    steps = [
        {
            "order": 1,
            "goal": "Set up your AWS account and local tooling",
            "action": "environment",
            "note": "Use an IAM user or role with least privilege, never root.",
        },
        {
            "order": 2,
            "goal": f"Provision the core services: {', '.join(project['services'])}",
            "action": "provision",
            "note": "Tag resources so cleanup and cost tracking stay simple.",
        },
        {
            "order": 3,
            "goal": "Wire the services together and configure permissions",
            "action": "configure",
            "note": "Grant only the actions each component needs, scoped by ARN.",
        },
        {
            "order": 4,
            "goal": "Deploy and test the end to end flow",
            "action": "deploy",
            "note": "Verify with a real request and read CloudWatch logs on errors.",
        },
        {
            "order": 5,
            "goal": "Clean up resources you no longer need",
            "action": "cleanup",
            "note": "Delete in reverse order of creation to avoid dependency errors.",
        },
    ]

    return {
        "found": True,
        "project": project,
        "estimated_hours": project["hours"],
        "steps": steps,
    }
