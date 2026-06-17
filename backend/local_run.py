"""Run the project generator agent locally from your terminal.

Usage:
    python local_run.py

You will need AWS credentials configured and Bedrock model access enabled for
the model id in agent/generator.py. This is the fastest way to see the agent
work before you deploy anything.
"""

from agent.generator import build_agent


def main() -> None:
    # callback_handler defaults to the console printer, so you see the agent
    # think and stream its answer in real time.
    agent = build_agent()

    print("Personalized AI Project Generator")
    print("Type your request, or 'quit' to exit.\n")
    print(
        "Example: I am an AWS Certified Cloud Practitioner. Suggest 3 "
        "beginner serverless projects I can finish in an afternoon.\n"
    )

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break
        if not user_input:
            continue

        print("\nagent> ", end="")
        agent(user_input)
        print("\n")


if __name__ == "__main__":
    main()
