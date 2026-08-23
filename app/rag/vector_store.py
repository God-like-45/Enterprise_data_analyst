from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.schemas.database_schema import TableSchema

logger = setup_logger(__name__)

class VectorStore:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        
        # Load a fast, free, local open-source embedding model
        logger.info("Loading local embedding model...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        self.collection_name = "database_schema_v2"
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Creates the Qdrant collection if it doesn't already exist."""
        collections = self.qdrant.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384, # The exact output size of all-MiniLM-L6-v2
                    distance=Distance.COSINE
                ),
            )

    def _get_embedding(self, text: str) -> list[float]:
        """Converts text into a vector using our local model."""
        # encode() returns a numpy array, we convert it to a standard Python list
        return self.embedding_model.encode(text).tolist()

    def index_schema(self, tables: list[TableSchema]):
        """Embeds and uploads database tables to Qdrant."""
        logger.info(f"Embedding and indexing {len(tables)} tables locally...")
        points = []
        
        for idx, table in enumerate(tables):
            llm_text = table.to_llm_string()
            vector = self._get_embedding(llm_text)
            
            points.append(
                PointStruct(
                    id=idx,
                    vector=vector,
                    payload={"table_name": table.table_name, "schema_text": llm_text}
                )
            )
            
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info("Schema successfully indexed in Qdrant.")

    def retrieve_relevant_tables(self, query: str, top_k: int = 3) -> str:
        """Embeds a question and retrieves relevant tables from Qdrant."""
        query_vector = self._get_embedding(query)
        
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )
        
        retrieved_schemas = []
        for hit in search_results:
            logger.info(f"Retrieved table: {hit.payload['table_name']} (Score: {hit.score:.2f})")
            retrieved_schemas.append(hit.payload['schema_text'])
            
        return "\n\n".join(retrieved_schemas)

vector_store = VectorStore()