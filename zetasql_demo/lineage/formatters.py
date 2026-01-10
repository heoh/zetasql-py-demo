"""Formatters for lineage results.

Provides JSON and human-readable text formatting for:
- TableLineage
- ColumnLineage
"""

import json
from typing import List, Union

from .models import ColumnEntity, ColumnLineage, TableLineage


class LineageFormatter:
    """Formatter for lineage results to JSON and text."""
    
    @staticmethod
    def to_json(
        lineage: Union[TableLineage, ColumnLineage, List[ColumnLineage]]
    ) -> str:
        """Convert lineage to JSON string.
        
        Args:
            lineage: TableLineage, ColumnLineage, or list of ColumnLineage
            
        Returns:
            Pretty-printed JSON string
            
        Example:
            >>> lineage = TableLineage(target="t1", sources={"t2"}, statement_type="INSERT")
            >>> print(LineageFormatter.to_json(lineage))
            {
              "target": "t1",
              "sources": ["t2"],
              "statement_type": "INSERT"
            }
        """
        if isinstance(lineage, TableLineage):
            return LineageFormatter._table_lineage_to_json(lineage)
        elif isinstance(lineage, list):
            return LineageFormatter._column_lineages_to_json(lineage)
        elif isinstance(lineage, ColumnLineage):
            return LineageFormatter._column_lineages_to_json([lineage])
        else:
            raise TypeError(f"Unsupported lineage type: {type(lineage)}")
    
    @staticmethod
    def to_text(
        lineage: Union[TableLineage, ColumnLineage, List[ColumnLineage]]
    ) -> str:
        """Convert lineage to human-readable text.
        
        Args:
            lineage: TableLineage, ColumnLineage, or list of ColumnLineage
            
        Returns:
            Formatted text string
            
        Example:
            >>> lineage = TableLineage(target="t1", sources={"t2"}, statement_type="INSERT")
            >>> print(LineageFormatter.to_text(lineage))
            Statement Type: INSERT
            Target: t1
            Sources:
              - t2
        """
        if isinstance(lineage, TableLineage):
            return LineageFormatter._table_lineage_to_text(lineage)
        elif isinstance(lineage, list):
            return LineageFormatter._column_lineages_to_text(lineage)
        elif isinstance(lineage, ColumnLineage):
            return LineageFormatter._column_lineages_to_text([lineage])
        else:
            raise TypeError(f"Unsupported lineage type: {type(lineage)}")
    
    @staticmethod
    def _table_lineage_to_json(lineage: TableLineage) -> str:
        """Convert TableLineage to JSON."""
        data = {
            "target": lineage.target,
            "sources": sorted(list(lineage.sources)),
            "statement_type": lineage.statement_type,
        }
        return json.dumps(data, indent=2)
    
    @staticmethod
    def _table_lineage_to_text(lineage: TableLineage) -> str:
        """Convert TableLineage to text."""
        lines = [
            f"Statement Type: {lineage.statement_type}",
        ]
        
        if lineage.target:
            lines.append(f"Target: {lineage.target}")
        else:
            lines.append("Target: (none - SELECT query)")
        
        lines.append("Sources:")
        if lineage.sources:
            for source in sorted(lineage.sources):
                lines.append(f"  - {source}")
        else:
            lines.append("  (no sources)")
        
        return "\n".join(lines)
    
    @staticmethod
    def _column_lineages_to_json(lineages: List[ColumnLineage]) -> str:
        """Convert list of ColumnLineage to JSON."""
        data = []
        for lineage in lineages:
            data.append({
                "target": {
                    "table": lineage.target.table,
                    "column": lineage.target.name,
                },
                "parents": [
                    {"table": parent.table, "column": parent.name}
                    for parent in sorted(lineage.parents, key=lambda p: (p.table, p.name))
                ],
            })
        return json.dumps(data, indent=2)
    
    @staticmethod
    def _column_lineages_to_text(lineages: List[ColumnLineage]) -> str:
        """Convert list of ColumnLineage to text.
        
        Format:
            target_table.column_name
                <- source_table1.column1
                <- source_table2.column2
        """
        if not lineages:
            return "(no column lineage)"
        
        lines = []
        for lineage in lineages:
            target_str = f"{lineage.target.table}.{lineage.target.name}"
            lines.append(target_str)
            
            if lineage.parents:
                for parent in sorted(lineage.parents, key=lambda p: (p.table, p.name)):
                    lines.append(f"    <- {parent.table}.{parent.name}")
            else:
                lines.append("    (no parent columns - literal or constant)")
            
            lines.append("")  # Empty line between entries
        
        return "\n".join(lines)
