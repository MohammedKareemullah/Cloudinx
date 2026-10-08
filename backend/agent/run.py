"""
Usage:
    python -m agent.run "Assess pwrds10 for AWS in us-east-1, all three scenarios"
    python -m agent.run            # interactive chat (type 'exit' to quit)
"""
import sys
from agent.strands_agent import build_agent


def main():
    agent = build_agent()
    if len(sys.argv) > 1:
        agent(" ".join(sys.argv[1:]))
        print()
        return
    print("Migration assessment agent (type 'exit' to quit)")
    while True:
        try:
            q = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("exit", "quit", ""):
            break
        agent(q)  # Strands streams the response to stdout by default
        print()


if __name__ == "__main__":
    main()
