import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue


class QdrantStorage:
    def __init__(self, url=None, collection="docs", dim=3072):
        # قراءة المسار من المتغيرات وتصحيحه للتشغيل المحلي
        raw_url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        if "http://qdrant" in raw_url:
            raw_url = raw_url.replace("http://qdrant", "http://localhost")

        self.client = QdrantClient(url=raw_url, timeout=30)
        self.collection = collection

        # إنشاء الـ Collection إذا لم تكن موجودة
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, ids, vectors, payloads):
        points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query_vector, top_k: int = 5, source_file: str = None):
        # تصفية البحث بناءً على اسم الملف المرفوع إذا تم تحديده
        query_filter = None
        if source_file:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source_file)
                    )
                ]
            )

        # تنفيذ عملية البحث مع دعم الإصدارات المختلفة من qdrant-client
        try:
            results = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                query_filter=query_filter,
                with_payload=True,
                limit=top_k
            ).points
        except AttributeError:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                query_filter=query_filter,
                with_payload=True,
                limit=top_k
            )

        contexts = []
        sources = set()

        for r in results:
            payload = getattr(r, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            if text:
                contexts.append(text)
                sources.add(source)

        return {"contexts": contexts, "sources": list(sources)}

    def clear_collection(self):
        """دالة اختيارية لمسح جميع الملفات القديمة وإعادة بناء الـ Collection"""
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(collection_name=self.collection)
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
            )