"""Table-level lineage extraction.

Extracts source and target tables from SQL statements using
ResolvedNodeVisitor to traverse the resolved AST.
"""

from typing import Set
from zetasql.api import ResolvedNodeVisitor
from zetasql.types import (
    ResolvedStatement,
    ResolvedTableScan,
    ResolvedCreateTableAsSelectStmt,
    ResolvedCreateViewStmt,
    ResolvedInsertStmt,
    ResolvedUpdateStmt,
    ResolvedMergeStmt,
    ResolvedDeleteStmt,
    ResolvedQueryStmt,
)
from .models import TableEntity, TableLineage


class TableLineageExtractor(ResolvedNodeVisitor):
    """Extract table-level lineage from resolved AST.
    
    Traverses the resolved AST to collect:
    - Source tables: All tables read by the query
    - Target table: The table being written to (if any)
    
    Attributes:
        source_tables: Set of source table entities
        target_table: Target table entity (None for SELECT-only)
        statement_type: Type of SQL statement
    """
    
    def __init__(self):
        """Initialize the extractor."""
        super().__init__()
        self.source_tables: Set[TableEntity] = set()
        self.target_table: TableEntity | None = None
        self.statement_type: str = ""
    
    def visit_ResolvedTableScan(self, node: ResolvedTableScan):
        """Visit table scan node - collect source table.
        
        Args:
            node: ResolvedTableScan node
        """
        if node.table and node.table.name:
            table_name = node.table.name
            self.source_tables.add(TableEntity(table_name))
        
        # Continue traversing children
        self.descend(node)
    
    def visit_ResolvedQueryStmt(self, node: ResolvedQueryStmt):
        """Visit query statement (SELECT).
        
        Args:
            node: ResolvedQueryStmt node
        """
        self.statement_type = "QUERY"
        self.descend(node)
    
    def visit_ResolvedCreateTableAsSelectStmt(self, node: ResolvedCreateTableAsSelectStmt):
        """Visit CREATE TABLE AS SELECT statement.
        
        Args:
            node: ResolvedCreateTableAsSelectStmt node
        """
        self.statement_type = "CREATE_TABLE_AS_SELECT"
        
        # Extract target table from name_path
        if node.name_path:
            table_name = ".".join(node.name_path)
            self.target_table = TableEntity(table_name)
        
        # Explicitly visit the query to extract source tables
        if node.query:
            self.visit(node.query)
        
        # Continue to extract source tables
        self.descend(node)
    
    def visit_ResolvedCreateViewStmt(self, node: ResolvedCreateViewStmt):
        """Visit CREATE VIEW statement.
        
        Args:
            node: ResolvedCreateViewStmt node
        """
        self.statement_type = "CREATE_VIEW"
        
        # Extract target view from name_path
        if node.name_path:
            view_name = ".".join(node.name_path)
            self.target_table = TableEntity(view_name)
        
        # Explicitly visit the query to extract source tables
        if node.query:
            self.visit(node.query)
        
        # Continue to extract source tables
        self.descend(node)
    
    def visit_ResolvedInsertStmt(self, node: ResolvedInsertStmt):
        """Visit INSERT statement.
        
        Args:
            node: ResolvedInsertStmt node
        """
        self.statement_type = "INSERT"
        
        # Extract target table from table_scan
        if node.table_scan and node.table_scan.table:
            table_name = node.table_scan.table.name
            self.target_table = TableEntity(table_name)
        
        # Continue to extract source tables (including the target table if it appears in SELECT)
        self.descend(node)
    
    def visit_ResolvedUpdateStmt(self, node: ResolvedUpdateStmt):
        """Visit UPDATE statement.
        
        Args:
            node: ResolvedUpdateStmt node
        """
        self.statement_type = "UPDATE"
        
        # Extract target table from table_scan
        if node.table_scan and node.table_scan.table:
            table_name = node.table_scan.table.name
            self.target_table = TableEntity(table_name)
        
        # Continue to extract source tables (can reference other tables in WHERE clause)
        self.descend(node)
    
    def visit_ResolvedMergeStmt(self, node: ResolvedMergeStmt):
        """Visit MERGE statement.
        
        Args:
            node: ResolvedMergeStmt node
        """
        self.statement_type = "MERGE"
        
        # Extract target table from table_scan
        if node.table_scan and node.table_scan.table:
            table_name = node.table_scan.table.name
            self.target_table = TableEntity(table_name)
        
        # Continue to extract source tables (USING clause)
        self.descend(node)
    
    def visit_ResolvedDeleteStmt(self, node: ResolvedDeleteStmt):
        """Visit DELETE statement.
        
        Args:
            node: ResolvedDeleteStmt node
        """
        self.statement_type = "DELETE"
        
        # Extract target table from table_scan
        if node.table_scan and node.table_scan.table:
            table_name = node.table_scan.table.name
            self.target_table = TableEntity(table_name)
        
        # Continue to extract source tables (can reference other tables in WHERE clause)
        self.descend(node)
    
    def default_visit(self, node):
        """Default visit behavior - traverse all children.
        
        Args:
            node: Any ResolvedNode
        """
        self.descend(node)


def extract_table_lineage(resolved_stmt: ResolvedStatement) -> TableLineage:
    """Extract table-level lineage from a resolved statement.
    
    Analyzes the resolved AST to determine:
    - Which tables are read (source tables)
    - Which table is written to (target table, if any)
    - The type of SQL statement
    
    Args:
        resolved_stmt: Analyzed SQL statement from ZetaSQL Analyzer
        
    Returns:
        TableLineage object containing source tables, target table, and statement type
        
    Example:
        >>> from zetasql.api import Analyzer
        >>> from src.zetasql_demo.catalog.sample_catalog import create_sample_catalog
        >>> from src.zetasql_demo.options.bigquery_options import get_bigquery_language_options
        >>> 
        >>> catalog = create_sample_catalog()
        >>> options = AnalyzerOptions(language_options=get_bigquery_language_options())
        >>> analyzer = Analyzer(options, catalog)
        >>> 
        >>> stmt = analyzer.analyze_statement("SELECT * FROM myproject.sales.orders")
        >>> lineage = extract_table_lineage(stmt)
        >>> print(f"Sources: {lineage.source_tables}")
        >>> print(f"Target: {lineage.target_table}")
    """
    extractor = TableLineageExtractor()
    extractor.visit(resolved_stmt)
    
    return TableLineage(
        target_table=extractor.target_table,
        source_tables=extractor.source_tables,
        statement_type=extractor.statement_type
    )
