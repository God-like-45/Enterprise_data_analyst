# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient
# pyrefly: ignore [missing-import]
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import requests
import re
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.schemas.database_schema import TableSchema

logger = setup_logger(__name__)

class VectorStore:
    def __init__(self):
        # --- QDRANT CONNECTION WITH DYNAMIC FALLBACK ---
        self.qdrant = None
        if settings.qdrant_url:
            try:
                logger.info(f"Connecting to Qdrant instance at {settings.qdrant_url}...")
                client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=getattr(settings, "qdrant_api_key", None),
                    timeout=5
                )
                # Health check to ensure the service is actually responding
                client.get_collections()
                self.qdrant = client
                logger.info("Successfully connected to Qdrant service.")
            except Exception as e:
                logger.warning(f"Could not connect to Qdrant at {settings.qdrant_url}: {e}. Falling back to in-memory Qdrant.")
                self.qdrant = QdrantClient(":memory:")
        else:
            logger.info("No QDRANT_URL configured. Initializing in-memory Qdrant instance...")
            self.qdrant = QdrantClient(":memory:")
        
        self.collection_name = "database_schema_v2"
        self._ensure_collection_exists()

        # --- SMART EMBEDDING ROUTER ---
        self.use_local_model = False
        try:
            # If running in GitHub Actions where we explicitly install it
            # pyrefly: ignore [missing-import]
            from sentence_transformers import SentenceTransformer
            logger.info("PyTorch detected. Loading local model for high-accuracy testing...")
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.use_local_model = True
        except ImportError:
            # If running on Render where it's absent from requirements.txt
            logger.info("PyTorch missing. Falling back to Hugging Face API for lightweight production...")

    def _ensure_collection_exists(self):
        """Creates the Qdrant collection if it doesn't already exist."""
        collections = self.qdrant.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384, # Output dimension of all-MiniLM-L6-v2
                    distance=Distance.COSINE
                ),
            )

    def _get_embedding(self, text: str) -> list[float]:
        """Routes vector generation dynamically based on the environment."""
        if self.use_local_model:
            return self.embedding_model.encode(text).tolist()
            
        # API Fallback for Render
        model_id = "sentence-transformers/all-MiniLM-L6-v2"
        api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_id}"
        
        try:
            response = requests.post(
                api_url, 
                json={"inputs": [text], "options": {"wait_for_model": True}},
                timeout=10
            )
            response.raise_for_status()
            return response.json()[0]
        except Exception as e:
            logger.error(f"Error fetching embeddings from API: {e}")
            return [0.0] * 384

    def index_schema(self, tables: list[TableSchema]):
        """Embeds and uploads database tables to Qdrant."""
        logger.info(f"Embedding and indexing {len(tables)} tables...")
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