"""Table-level lineage extraction.

Extracts source and target tables from ZetaSQL resolved statements.
Supports all statement types from zetasql-toolkit.
"""

from typing import Set, Optional

from zetasql.api import ResolvedNodeVisitor
from zetasql.types import (
    ResolvedStatement,
    ResolvedTableScan,
    ResolvedTVFScan,
    ResolvedQueryStmt,
    ResolvedCreateTableAsSelectStmt,
    ResolvedCreateViewStmt,
    ResolvedCreateMaterializedViewStmt,
    ResolvedInsertStmt,
    ResolvedUpdateStmt,
    ResolvedMergeStmt,
)

from .models import TableLineage


class TableLineageExtractor(ResolvedNodeVisitor):
    """Extracts table-level lineage from resolved statements using Visitor pattern.
    
    Traverses the resolved AST to collect:
    - Source tables (from ResolvedTableScan and ResolvedTVFScan)
    - Target table (from statement-specific nodes)
    """
    
    def __init__(self):
        """Initialize the extractor with empty collections."""
        super().__init__()
        self.source_tables: Set[str] = set()
        self.target_table: Optional[str] = None
        self.statement_type: str = "UNKNOWN"
    
    def visit_ResolvedTableScan(self, node: ResolvedTableScan):
        """Visit ResolvedTableScan to collect source table names.
        
        Args:
            node: ResolvedTableScan node containing table information
        """
        if node.table and hasattr(node.table, 'name'):
            table_name = node.table.name
            self.source_tables.add(table_name)
        
        # Continue traversing children
        self.descend(node)
    
    def visit_ResolvedProjectScan(self, node):
        """Visit project scan and continue traversal."""
        if hasattr(node, 'input_scan') and node.input_scan:
            self.visit(node.input_scan)
        self.descend(node)
    
    def visit_ResolvedAggregateScan(self, node):
        """Visit aggregate scan and continue traversal."""
        if hasattr(node, 'input_scan') and node.input_scan:
            self.visit(node.input_scan)
        self.descend(node)
    
    def visit_ResolvedJoinScan(self, node):
        """Visit join scan and continue traversal."""
        if hasattr(node, 'left_scan') and node.left_scan:
            self.visit(node.left_scan)
        if hasattr(node, 'right_scan') and node.right_scan:
            self.visit(node.right_scan)
        self.descend(node)
    
    def visit_ResolvedFilterScan(self, node):
        """Visit filter scan and continue traversal."""
        if hasattr(node, 'input_scan') and node.input_scan:
            self.visit(node.input_scan)
        self.descend(node)
    
    def visit_ResolvedWithScan(self, node):
        """Visit WITH scan (CTE) and continue traversal."""
        # Visit CTE definitions
        if hasattr(node, 'with_entry_list'):
            for entry in node.with_entry_list:
                if hasattr(entry, 'with_subquery') and entry.with_subquery:
                    self.visit(entry.with_subquery)
        # Visit main query
        if hasattr(node, 'query') and node.query:
            self.visit(node.query)
        self.descend(node)
    
    def visit_ResolvedTVFScan(self, node: ResolvedTVFScan):
        """Visit ResolvedTVFScan to collect table-valued function references.
        
        Args:
            node: ResolvedTVFScan node containing TVF information
        """
        # TVF scans can also be considered as source tables
        if node.tvf and hasattr(node.tvf, 'name'):
            tvf_name = node.tvf.name
            if tvf_name:
                self.source_tables.add(tvf_name)
        
        self.descend(node)
    
    def visit_ResolvedQueryStmt(self, node: ResolvedQueryStmt):
        """Visit ResolvedQueryStmt (SELECT statement).
        
        Args:
            node: ResolvedQueryStmt node
        """
        self.statement_type = "SELECT"
        # SELECT has no target table
        self.target_table = None
        
        # Explicitly visit the query to collect source tables
        if hasattr(node, 'query') and node.query:
            self.visit(node.query)
        
        # Continue traversing other fields
        self.descend(node)
    
    def visit_ResolvedCreateTableAsSelectStmt(self, node: ResolvedCreateTableAsSelectStmt):
        """Visit ResolvedCreateTableAsSelectStmt.
        
        Args:
            node: ResolvedCreateTableAsSelectStmt node
        """
        self.statement_type = "CREATE_TABLE_AS_SELECT"
        # Get target table from name_path
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        
        # Explicitly visit the query
        if hasattr(node, 'query') and node.query:
            self.visit(node.query)
        
        # Descend will visit the query and collect source tables
        self.descend(node)
    
    def visit_ResolvedCreateViewStmt(self, node: ResolvedCreateViewStmt):
        """Visit ResolvedCreateViewStmt.
        
        Args:
            node: ResolvedCreateViewStmt node
        """
        self.statement_type = "CREATE_VIEW"
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        
        # Explicitly visit the query to collect source tables
        # descend() may not automatically visit the query field
        if hasattr(node, 'query') and node.query:
            self.visit(node.query)
        
        # Still call descend for other fields
        self.descend(node)
    
    def visit_ResolvedCreateMaterializedViewStmt(self, node: ResolvedCreateMaterializedViewStmt):
        """Visit ResolvedCreateMaterializedViewStmt.
        
        Args:
            node: ResolvedCreateMaterializedViewStmt node
        """
        self.statement_type = "CREATE_MATERIALIZED_VIEW"
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        self.descend(node)
    
    def visit_ResolvedInsertStmt(self, node: ResolvedInsertStmt):
        """Visit ResolvedInsertStmt.
        
        Args:
            node: ResolvedInsertStmt node
        """
        self.statement_type = "INSERT"
        # Get target table from table_scan
        if node.table_scan and node.table_scan.table:
            self.target_table = node.table_scan.table.name
        
        # Explicitly visit query/row to collect source tables
        if hasattr(node, 'query') and node.query:
            self.visit(node.query)
        if hasattr(node, 'row') and node.row:
            self.visit(node.row)
        
        self.descend(node)
    
    def visit_ResolvedUpdateStmt(self, node: ResolvedUpdateStmt):
        """Visit ResolvedUpdateStmt.
        
        Args:
            node: ResolvedUpdateStmt node
        """
        self.statement_type = "UPDATE"
        # Get target table from table_scan
        if node.table_scan and node.table_scan.table:
            self.target_table = node.table_scan.table.name
            # UPDATE also reads from the target table
            self.source_tables.add(self.target_table)
        self.descend(node)
    
    def visit_ResolvedMergeStmt(self, node: ResolvedMergeStmt):
        """Visit ResolvedMergeStmt.
        
        Args:
            node: ResolvedMergeStmt node
        """
        self.statement_type = "MERGE"
        # Get target table from table_scan
        if node.table_scan and node.table_scan.table:
            self.target_table = node.table_scan.table.name
            # MERGE also reads from the target table
            self.source_tables.add(self.target_table)
        self.descend(node)


def extract_table_lineage(stmt: ResolvedStatement) -> TableLineage:
    """Extract table-level lineage from a resolved statement.
    
    Entry point function for table lineage extraction.
    
    Args:
        stmt: ResolvedStatement to extract lineage from
        
    Returns:
        TableLineage object containing source tables, target table, and statement type
        
    Example:
        >>> sql = "CREATE TABLE t1 AS SELECT * FROM t2 JOIN t3"
        >>> stmt = analyzer.analyze_statement(sql)
        >>> lineage = extract_table_lineage(stmt)
        >>> print(lineage.target)  # "t1"
        >>> print(lineage.sources)  # {"t2", "t3"}
    """
    extractor = TableLineageExtractor()
    extractor.visit(stmt)
    
    return TableLineage(
        target=extractor.target_table,
        sources=extractor.source_tables,
        statement_type=extractor.statement_type
    )
