from sqlalchemy import MetaData
from app.database.connection import db_manager
from app.schemas.database_schema import TableSchema, ColumnSchema
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class SchemaExtractor:
    def __init__(self):
        self.engine = db_manager.engine
        # MetaData is a SQLAlchemy registry that holds schema information
        self.metadata = MetaData()

    def extract_schema(self) -> list[TableSchema]:
        """
        Reflects the database and extracts table, column, and foreign key metadata.
        """
        logger.info("Starting database schema extraction...")
        
        # This single line commands SQLAlchemy to query the DB and map all tables
        self.metadata.reflect(bind=self.engine)
        
        extracted_tables = []
        
        for table_name, table_obj in self.metadata.tables.items():
            columns = []
            
            for col in table_obj.columns:
                # Determine foreign key relationships
                fk_target = None
                if col.foreign_keys:
                    # Get the first foreign key target (e.g., 'customers.customer_id')
                    fk = list(col.foreign_keys)[0]
                    fk_target = fk.target_fullname

                column_schema = ColumnSchema(
                    name=col.name,
                    data_type=str(col.type),
                    is_primary=col.primary_key,
                    foreign_key_target=fk_target
                )
                columns.append(column_schema)
                
            table_schema = TableSchema(
                table_name=table_name,
                columns=columns
            )
            extracted_tables.append(table_schema)
            
        logger.info(f"Successfully extracted {len(extracted_tables)} tables.")
        return extracted_tables

# Instantiate for use across the app
schema_extractor = SchemaExtractor()