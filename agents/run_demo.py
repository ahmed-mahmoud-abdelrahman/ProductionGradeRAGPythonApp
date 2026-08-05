"""Simple demo to exercise the agents locally."""

from agents.coordinator import handle_request


def main():
    query = "Explain what RAG is and give a short example."
    result = handle_request(query)
    print("Result:")
    print(result["answer"] if isinstance(result, dict) else result)


if __name__ == "__main__":
    main()
