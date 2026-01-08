"""Data models for lineage extraction.

Python port of Java data classes from zetasql-toolkit:
- ColumnEntity.java
- ColumnLineage.java
- TableLineage (new, for table-level lineage)
"""

from dataclasses import dataclass, field
from typing import Optional, Set

from zetasql.types import ResolvedColumn


@dataclass(frozen=True)
class ColumnEntity:
    """Represents a column in a table.
    
    Python port of ColumnEntity.java
    
    Attributes:
        table: Fully qualified table name (e.g., "project.dataset.table")
        name: Column name
    """
    table: str
    name: str
    
    @staticmethod
    def from_resolved_column(resolved_column: ResolvedColumn) -> "ColumnEntity":
        """Create ColumnEntity from a ResolvedColumn.
        
        Args:
            resolved_column: ZetaSQL ResolvedColumn
            
        Returns:
            ColumnEntity with table and column name from ResolvedColumn
        """
        return ColumnEntity(
            table=resolved_column.table_name,
            name=resolved_column.name
        )
    
    def __hash__(self):
        """Custom hash for case-insensitive column name comparison."""
        return hash((self.table, self.name.lower()))
    
    def __eq__(self, other):
        """Custom equality for case-insensitive column name comparison."""
        if not isinstance(other, ColumnEntity):
            return False
        return self.table == other.table and self.name.lower() == other.name.lower()


@dataclass(frozen=True)
class ColumnLineage:
    """Represents column-level lineage relationship.
    
    Python port of ColumnLineage.java
    
    Attributes:
        target: Target column (output)
        parents: Set of parent columns (inputs/sources)
    """
    target: ColumnEntity
    parents: frozenset  # frozenset[ColumnEntity] for hashability
    
    def __init__(self, target: ColumnEntity, parents: Set[ColumnEntity]):
        """Initialize ColumnLineage with target and parent columns.
        
        Args:
            target: Target column
            parents: Set of parent columns
        """
        object.__setattr__(self, 'target', target)
        object.__setattr__(self, 'parents', frozenset(parents))


@dataclass
class TableLineage:
    """Represents table-level lineage relationship.
    
    New class for tracking table-level dependencies.
    
    Attributes:
        target: Target table name (None for SELECT queries without CREATE/INSERT)
        sources: Set of source table names
        statement_type: Type of SQL statement (SELECT, INSERT, UPDATE, etc.)
    """
    target: Optional[str] = None
    sources: Set[str] = field(default_factory=set)
    statement_type: str = "UNKNOWN"
