# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient
# pyrefly: ignore [missing-import]
from qdrant_client.models import Distance, VectorParams, PointStruct
import requests
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.schemas.database_schema import TableSchema

logger = setup_logger(__name__)

class VectorStore:
    def __init__(self):
        # Fallback to in-memory Qdrant if running locally or without a remote Qdrant Cloud service
        if not settings.qdrant_url or "localhost" in settings.qdrant_url:
            logger.info("Initializing in-memory Qdrant instance for cloud/lightweight deployment...")
            self.qdrant = QdrantClient(":memory:")
        else:
            logger.info(f"Connecting to remote Qdrant instance at {settings.qdrant_url}")
            self.qdrant = QdrantClient(
                url=settings.qdrant_url,
                api_key=getattr(settings, "qdrant_api_key", None)
            )
        
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
                    size=384, # The exact output dimension of all-MiniLM-L6-v2
                    distance=Distance.COSINE
                ),
            )

    def _get_embedding(self, text: str) -> list[float]:
        """Converts text into a vector using Hugging Face's free external API (Zero local RAM required)."""
        model_id = "sentence-transformers/all-MiniLM-L6-v2"
        api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_id}"
        
        try:
            response = requests.post(
                api_url, 
                json={"inputs": [text], "options": {"wait_for_model": True}}
            )
            response.raise_for_status()
            # The API returns a list of embeddings. Extract index 0 for single string input.
            return response.json()[0]
        except Exception as e:
            logger.error(f"Error fetching embeddings from API: {e}")
            # Fallback to a zero-vector so the Qdrant insertion doesn't crash on network failure
            return [0.0] * 384

    def index_schema(self, tables: list[TableSchema]):
        """Embeds and uploads database tables to Qdrant."""
        logger.info(f"Embedding and indexing {len(tables)} tables via API...")
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
        """Embeds a question and retrieves relevant tables from Qdrant, with relationship expansion."""
        # pyrefly: ignore [missing-import]
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        import re
        
        query_vector = self._get_embedding(query)
        
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )
        
        retrieved_schemas = []
        retrieved_names = set()
        
        for hit in search_results:
            name = hit.payload['table_name']
            retrieved_names.add(name)
            retrieved_schemas.append(hit.payload['schema_text'])
            logger.info(f"Retrieved table: {name} (Score: {hit.score:.2f})")
            
        # Relationship Expansion: Find foreign key dependencies
        extra_tables_needed = set()
        for schema_text in list(retrieved_schemas):
            # Look for "-> REFERENCES tablename.columnname"
            matches = re.findall(r'REFERENCES\s+([a-zA-Z0-9_]+)\.', schema_text)
            for m in matches:
                if m not in retrieved_names:
                    extra_tables_needed.add(m)
                    
        # Fetch any missing linked tables directly by name
        for table_name in extra_tables_needed:
            try:
                res, _ = self.qdrant.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="table_name", match=MatchValue(value=table_name))]
                    ),
                    limit=1
                )
                if res:
                    retrieved_schemas.append(res[0].payload['schema_text'])
                    retrieved_names.add(table_name)
                    logger.info(f"Relationship Expansion: Auto-included table '{table_name}'")
            except Exception as e:
                logger.warning(f"Failed to fetch linked table {table_name}: {e}")
                
        return "\n\n".join(retrieved_schemas)

vector_store = VectorStore()