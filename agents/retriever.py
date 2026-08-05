"""Retriever agent stub that wraps the project's vector DB if available."""


class Retriever:
    def __init__(self, vector_db=None):
        self.vector_db = vector_db

    def search(self, query: str, top_k: int = 5):
        """Search for relevant documents.

        If a `vector_db` with a `search` method is provided, defer to it; otherwise
        return a small placeholder result set.
        """
        if self.vector_db and hasattr(self.vector_db, "search"):
            return self.vector_db.search(query, top_k=top_k)

        # Placeholder result for offline development
        return [{"id": 0, "text": f"(placeholder) result for query: {query}"}]
