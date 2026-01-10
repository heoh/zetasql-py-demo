"""Table-level lineage extraction using ResolvedNodeVisitor.

Extracts source and target tables from SQL statements:
- SELECT, CREATE TABLE AS SELECT, CREATE VIEW
- INSERT, UPDATE, MERGE
"""

from typing import Optional, Set

from zetasql.api import ResolvedNodeVisitor
from zetasql.types import ResolvedStatement

from .models import TableLineage


class TableLineageExtractor(ResolvedNodeVisitor):
    """Visitor for extracting table-level lineage from resolved statements.
    
    Traverses the resolved AST to collect:
    - Source tables (from ResolvedTableScan nodes)
    - Target table (from statement type-specific nodes)
    - Statement type
    
    Example:
        >>> extractor = TableLineageExtractor()
        >>> extractor.visit(resolved_statement)
        >>> lineage = extractor.get_lineage()
    """
    
    def __init__(self):
        super().__init__()
        self.source_tables: Set[str] = set()
        self.target_table: Optional[str] = None
        self.statement_type: str = "UNKNOWN"
    
    def get_lineage(self) -> TableLineage:
        """Get the extracted table lineage.
        
        Returns:
            TableLineage with target, sources, and statement type
        """
        return TableLineage(
            target=self.target_table,
            sources=self.source_tables.copy(),
            statement_type=self.statement_type
        )
    
    def visit_ResolvedTableScan(self, node):
        """Visit table scan nodes to collect source tables.
        
        Args:
            node: ResolvedTableScan node
        """
        if node.table and node.table.name:
            self.source_tables.add(node.table.name)
        self.descend(node)
    
    def visit_ResolvedQueryStmt(self, node):
        """Visit SELECT statements.
        
        Args:
            node: ResolvedQueryStmt node
        """
        self.statement_type = "SELECT"
        self.descend(node)
    
    def visit_ResolvedCreateTableAsSelectStmt(self, node):
        """Visit CREATE TABLE AS SELECT statements.
        
        Args:
            node: ResolvedCreateTableAsSelectStmt node
        """
        self.statement_type = "CREATE_TABLE_AS_SELECT"
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        self.descend(node)
    
    def visit_ResolvedCreateViewStmt(self, node):
        """Visit CREATE VIEW statements.
        
        Args:
            node: ResolvedCreateViewStmt node
        """
        self.statement_type = "CREATE_VIEW"
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        self.descend(node)
    
    def visit_ResolvedCreateMaterializedViewStmt(self, node):
        """Visit CREATE MATERIALIZED VIEW statements.
        
        Args:
            node: ResolvedCreateMaterializedViewStmt node
        """
        self.statement_type = "CREATE_VIEW"
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        self.descend(node)
    
    def visit_ResolvedInsertStmt(self, node):
        """Visit INSERT statements.
        
        Args:
            node: ResolvedInsertStmt node
        """
        self.statement_type = "INSERT"
        if node.table_scan and node.table_scan.table:
            self.target_table = node.table_scan.table.name
        self.descend(node)
    
    def visit_ResolvedUpdateStmt(self, node):
        """Visit UPDATE statements.
        
        Args:
            node: ResolvedUpdateStmt node
        """
        self.statement_type = "UPDATE"
        if node.table_scan and node.table_scan.table:
            self.target_table = node.table_scan.table.name
        self.descend(node)
    
    def visit_ResolvedMergeStmt(self, node):
        """Visit MERGE statements.
        
        Args:
            node: ResolvedMergeStmt node
        """
        self.statement_type = "MERGE"
        if node.table_scan and node.table_scan.table:
            self.target_table = node.table_scan.table.name
        self.descend(node)


def extract_table_lineage(statement: ResolvedStatement) -> TableLineage:
    """Extract table-level lineage from a resolved statement.
    
    Args:
        statement: ResolvedStatement from ZetaSQL analysis
        
    Returns:
        TableLineage containing target, sources, and statement type
        
    Example:
        >>> from zetasql.api import Analyzer
        >>> analyzer = Analyzer(options, catalog)
        >>> stmt = analyzer.analyze_statement("SELECT * FROM table1")
        >>> lineage = extract_table_lineage(stmt)
        >>> print(lineage.sources)
        {'table1'}
    """
    extractor = TableLineageExtractor()
    extractor.visit(statement)
    return extractor.get_lineage()
