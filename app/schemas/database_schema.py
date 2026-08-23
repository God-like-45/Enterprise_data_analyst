from pydantic import BaseModel
from typing import List, Optional

class ColumnSchema(BaseModel):
    name: str
    data_type: str
    is_primary: bool
    foreign_key_target: Optional[str] = None

class TableSchema(BaseModel):
    table_name: str
    columns: List[ColumnSchema]
    
    def to_llm_string(self) -> str:
        """
        Converts the table schema into a clean, readable string optimized 
        for an LLM's context window.
        """
        lines = [f"Table: {self.table_name}"]
        lines.append("Columns:")
        
        for col in self.columns:
            pk_str = " (PRIMARY KEY)" if col.is_primary else ""
            fk_str = f" -> REFERENCES {col.foreign_key_target}" if col.foreign_key_target else ""
            lines.append(f"  - {col.name} ({col.data_type}){pk_str}{fk_str}")
            
        return "\n".join(lines)