"""Data models for lineage extraction."""

from dataclasses import dataclass, field
from typing import Set


@dataclass(frozen=True)
class TableEntity:
    """Represents a table entity.
    
    Attributes:
        name: Full table name (e.g., "myproject.sales.orders")
    """
    name: str
    
    @property
    def simple_name(self) -> str:
        """Return the last part of the table name.
        
        Returns:
            Simple table name (e.g., "orders" from "myproject.sales.orders")
        """
        parts = self.name.split(".")
        return parts[-1] if parts else self.name
    
    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ColumnEntity:
    """Represents a column entity.
    
    Attributes:
        table: Full table name
        column: Column name
    """
    table: str
    column: str
    
    def __str__(self) -> str:
        return f"{self.table}.{self.column}"


@dataclass
class TableLineage:
    """Represents table-level lineage.
    
    Attributes:
        target_table: Target table (None for SELECT-only statements)
        source_tables: Set of source tables
        statement_type: SQL statement type (e.g., "SELECT", "CREATE_TABLE_AS_SELECT")
    """
    target_table: TableEntity | None
    source_tables: Set[TableEntity] = field(default_factory=set)
    statement_type: str = ""


@dataclass
class ColumnLineage:
    """Represents column-level lineage.
    
    Attributes:
        target: Target column
        parents: Set of parent (source) columns
    """
    target: ColumnEntity
    parents: Set[ColumnEntity] = field(default_factory=set)
