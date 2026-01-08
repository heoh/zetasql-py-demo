"""Data models for lineage extraction.

Python port of Java classes from zetasql-toolkit:
- ColumnEntity.java
- ColumnLineage.java
- TableLineage (new for Python)
"""

from dataclasses import dataclass, field
from typing import Optional, Set

from zetasql.types import ResolvedColumn


@dataclass(frozen=True)
class ColumnEntity:
    """Represents a column in a table.
    
    Port of ColumnEntity.java from zetasql-toolkit.
    
    Attributes:
        table: Fully qualified table name (e.g., "project.dataset.table")
        name: Column name
        
    Example:
        >>> entity = ColumnEntity("project.dataset.table", "column_name")
        >>> entity.table
        'project.dataset.table'
    """
    table: str
    name: str
    
    @staticmethod
    def from_resolved_column(resolved_column: ResolvedColumn) -> "ColumnEntity":
        """Create ColumnEntity from ResolvedColumn.
        
        Args:
            resolved_column: ResolvedColumn from ZetaSQL analysis
            
        Returns:
            ColumnEntity instance
            
        Example:
            >>> # resolved_column from analyzed statement
            >>> entity = ColumnEntity.from_resolved_column(resolved_column)
        """
        return ColumnEntity(
            table=resolved_column.table_name,
            name=resolved_column.name
        )
    
    def __hash__(self):
        """Hash using table name and lowercase column name for case-insensitive comparison."""
        return hash((self.table, self.name.lower()))
    
    def __eq__(self, other):
        """Equality check with case-insensitive column name comparison."""
        if not isinstance(other, ColumnEntity):
            return False
        return (
            self.table == other.table and
            self.name.lower() == other.name.lower()
        )


@dataclass(frozen=True)
class ColumnLineage:
    """Represents column-level lineage.
    
    Port of ColumnLineage.java from zetasql-toolkit.
    Shows which source columns a target column depends on.
    
    Attributes:
        target: Target column entity
        parents: Set of source column entities (terminal columns from tables)
        
    Example:
        >>> target = ColumnEntity("target_table", "result_col")
        >>> parents = {
        ...     ColumnEntity("source1", "col1"),
        ...     ColumnEntity("source2", "col2")
        ... }
        >>> lineage = ColumnLineage(target, parents)
    """
    target: ColumnEntity
    parents: Set[ColumnEntity] = field(default_factory=set)
    
    def __hash__(self):
        """Hash using target and frozenset of parents."""
        return hash((self.target, frozenset(self.parents)))


@dataclass
class TableLineage:
    """Represents table-level lineage.
    
    New class for Python implementation (not in Java toolkit).
    Shows which source tables are used to write to a target table.
    
    Attributes:
        target: Target table name (None for SELECT queries)
        sources: Set of source table names
        statement_type: Type of SQL statement (SELECT, INSERT, UPDATE, etc.)
        
    Example:
        >>> lineage = TableLineage(
        ...     target="project.dataset.target",
        ...     sources={"project.dataset.source1", "project.dataset.source2"},
        ...     statement_type="INSERT"
        ... )
    """
    target: Optional[str] = None
    sources: Set[str] = field(default_factory=set)
    statement_type: str = "UNKNOWN"
