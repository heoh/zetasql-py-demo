"""Column-level lineage extraction.

Extracts column-level lineage from SQL statements using BFS to find
terminal parent columns.
"""

from typing import List, Set
from collections import deque
from zetasql.api import ResolvedNodeVisitor
from zetasql.types import (
    ResolvedStatement,
    ResolvedNode,
    ResolvedColumn,
    ResolvedColumnRef,
    ResolvedExpr,
    ResolvedQueryStmt,
    ResolvedCreateTableAsSelectStmt,
    ResolvedCreateViewStmt,
    ResolvedInsertStmt,
    ResolvedOutputColumn,
)
from .models import ColumnEntity, ColumnLineage


class ParentColumnFinder(ResolvedNodeVisitor):
    """Find terminal parent columns for an expression using BFS.
    
    Traverses the expression tree to find all ResolvedColumnRef nodes,
    which represent the actual source columns.
    
    Attributes:
        parents: Set of terminal parent ColumnEntity objects
        cte_column_map: Mapping from CTE name to column sources
    """
    
    def __init__(self, cte_column_map: dict | None = None):
        """Initialize the finder.
        
        Args:
            cte_column_map: Optional CTE name -> {col_name: Set[ColumnEntity]} mapping
        """
        super().__init__()
        self.parents: Set[ColumnEntity] = set()
        self.cte_column_map = cte_column_map or {}
    
    def visit_ResolvedColumnRef(self, node: ResolvedColumnRef):
        """Visit column reference - add to parent columns.
        
        Args:
            node: ResolvedColumnRef node
        """
        if node.column:
            col = node.column
            table_name = col.table_name if col.table_name else None
            column_name = col.name
            
            if table_name and column_name:
                # Check if this is a CTE reference
                if table_name in self.cte_column_map:
                    # Resolve CTE column to actual sources
                    cte_info = self.cte_column_map[table_name]
                    col_map_by_name = cte_info.get('by_name', {})
                    
                    if column_name in col_map_by_name:
                        # Add all source columns from CTE
                        self.parents.update(col_map_by_name[column_name])
                    else:
                        self.parents.add(ColumnEntity(table_name, column_name))
                else:
                    self.parents.add(ColumnEntity(table_name, column_name))
        
        # Continue traversing
        self._traverse_children(node)
    
    def default_visit(self, node: ResolvedNode):
        """Default visitor - traverse all children.
        
        Args:
            node: Any ResolvedNode
        """
        self._traverse_children(node)
    
    def _traverse_children(self, node: ResolvedNode):
        """Manually traverse all child nodes.
        
        Args:
            node: Node to traverse
        """
        # Handle common child patterns
        if hasattr(node, 'argument_list'):
            for arg in node.argument_list:
                self.visit(arg)
        
        if hasattr(node, 'expr'):
            if node.expr:
                self.visit(node.expr)
        
        if hasattr(node, 'condition'):
            if node.condition:
                self.visit(node.condition)
        
        if hasattr(node, 'then_expr'):
            if node.then_expr:
                self.visit(node.then_expr)
        
        if hasattr(node, 'else_expr'):
            if node.else_expr:
                self.visit(node.else_expr)
        
        # For other nodes, use descend
        self.descend(node)


def find_parents(expr: ResolvedExpr, cte_column_map: dict | None = None) -> Set[ColumnEntity]:
    """Find all terminal parent columns for an expression.
    
    Uses BFS to traverse the expression tree and collect all source columns.
    
    Args:
        expr: Expression to analyze
        cte_column_map: Optional CTE name -> {col_name: Set[ColumnEntity]} mapping
        
    Returns:
        Set of parent ColumnEntity objects
    """
    finder = ParentColumnFinder(cte_column_map)
    finder.visit(expr)
    return finder.parents


class ColumnLineageExtractor(ResolvedNodeVisitor):
    """Extract column-level lineage from resolved AST.
    
    Traverses the resolved AST to collect lineage for each output column.
    
    Attributes:
        lineages: List of ColumnLineage objects
        target_table: Target table name (for CREATE/INSERT statements)
    """
    
    def __init__(self):
        """Initialize the extractor."""
        super().__init__()
        self.lineages: List[ColumnLineage] = []
        self.target_table: str | None = None
    
    def visit_ResolvedQueryStmt(self, node: ResolvedQueryStmt):
        """Visit query statement (SELECT).
        
        Args:
            node: ResolvedQueryStmt node
        """
        # SELECT has no target table
        self.target_table = None
        
        # Process query to extract column lineage
        if node.query:
            self._process_scan(node.query, node.output_column_list)
        
        self.descend(node)
    
    def visit_ResolvedCreateTableAsSelectStmt(self, node: ResolvedCreateTableAsSelectStmt):
        """Visit CREATE TABLE AS SELECT statement.
        
        Args:
            node: ResolvedCreateTableAsSelectStmt node
        """
        # Extract target table
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        
        # Process query to extract column lineage
        if node.query:
            self._process_scan(node.query, node.output_column_list)
        
        self.descend(node)
    
    def visit_ResolvedCreateViewStmt(self, node: ResolvedCreateViewStmt):
        """Visit CREATE VIEW statement.
        
        Args:
            node: ResolvedCreateViewStmt node
        """
        # Extract target view
        if node.name_path:
            self.target_table = ".".join(node.name_path)
        
        # Process query to extract column lineage
        if node.query:
            self._process_scan(node.query, node.output_column_list)
        
        self.descend(node)
    
    def visit_ResolvedInsertStmt(self, node: ResolvedInsertStmt):
        """Visit INSERT statement.
        
        Args:
            node: ResolvedInsertStmt node
        """
        # Extract target table
        if node.table_scan and node.table_scan.table:
            self.target_table = node.table_scan.table.name
        
        # Process insert columns
        if node.insert_column_list and node.query:
            # Build column expr map from query
            column_expr_map = {}
            self._build_column_expr_map(node.query, column_expr_map)
            
            # Get query column list
            query_columns = node.query.column_list if hasattr(node.query, 'column_list') else []
            
            # Match insert columns with query columns
            for i, insert_col in enumerate(node.insert_column_list):
                if i < len(query_columns):
                    query_col = query_columns[i]
                    
                    target_col = ColumnEntity(self.target_table, insert_col.name)
                    
                    # Find parent columns
                    column_id = query_col.column_id
                    
                    if column_id in column_expr_map:
                        # Computed column
                        expr = column_expr_map[column_id]
                        parent_cols = find_parents(expr)
                    else:
                        # Direct column reference
                        if query_col.table_name and query_col.name:
                            parent_cols = {ColumnEntity(query_col.table_name, query_col.name)}
                        else:
                            parent_cols = set()
                    
                    lineage = ColumnLineage(
                        target=target_col,
                        parents=parent_cols
                    )
                    self.lineages.append(lineage)
        
        self.descend(node)
    
    def _process_scan(self, scan_node: ResolvedNode, output_columns: list):
        """Process a scan node to extract column lineage.
        
        Args:
            scan_node: ResolvedScan node (e.g., ResolvedProjectScan)
            output_columns: List of ResolvedOutputColumn objects
        """
        # Build mapping from column_id to expression
        column_expr_map = {}
        
        # Build CTE mapping (CTE name -> column mappings)
        cte_column_map = {}
        self._build_cte_column_map(scan_node, cte_column_map)
        
        
        # Traverse the scan tree to find all computed columns
        self._build_column_expr_map(scan_node, column_expr_map)
        
        # Process each output column
        for output_col in output_columns:
            target_col = ColumnEntity(self.target_table, output_col.name)
            
            
            # Find parent columns for this output column
            if output_col.column:
                column_id = output_col.column.column_id
                col_table = output_col.column.table_name
                col_name = output_col.column.name
                
                
                if column_id in column_expr_map:
                    # Column has an expression, find its parents
                    expr = column_expr_map[column_id]
                    parent_cols = find_parents(expr, cte_column_map)
                else:
                    # Direct column reference
                    col = output_col.column
                    if col.table_name and col.name:
                        # Check if this is a CTE reference
                        if col.table_name in cte_column_map:
                            # Resolve CTE column to actual source
                            cte_info = cte_column_map[col.table_name]
                            
                            # Try by name first (handles aliases)
                            col_map_by_name = cte_info.get('by_name', {})
                            if col.name in col_map_by_name:
                                parent_cols = col_map_by_name[col.name]
                            else:
                                # Try by column_id
                                col_id_map = cte_info.get('by_id', {})
                                if column_id in col_id_map:
                                    parent_cols = col_id_map[column_id]
                                else:
                                    parent_cols = {ColumnEntity(col.table_name, col.name)}
                        else:
                            parent_cols = {ColumnEntity(col.table_name, col.name)}
                    else:
                        parent_cols = set()
            else:
                parent_cols = set()
            
            lineage = ColumnLineage(
                target=target_col,
                parents=parent_cols
            )
            self.lineages.append(lineage)
    
    def _build_cte_column_map(self, node: ResolvedNode, cte_column_map: dict):
        """Build a mapping from CTE name to column sources.
        
        Args:
            node: Node to traverse
            cte_column_map: Dictionary to populate with CTE_name -> {col_name: Set[ColumnEntity]}
        """
        # Check for WITH entry list
        if hasattr(node, 'with_entry_list'):
            for entry in node.with_entry_list:
                if hasattr(entry, 'with_query_name') and hasattr(entry, 'with_subquery'):
                    cte_name = entry.with_query_name
                    subquery = entry.with_subquery
                    
                    
                    # First, recursively build CTE maps for nested CTEs within this subquery
                    self._build_cte_column_map(subquery, cte_column_map)
                    
                    # Build column expression map for this CTE
                    cte_expr_map = {}
                    self._build_column_expr_map(subquery, cte_expr_map)
                    
                    
                    # Map CTE columns to their source columns using BOTH name and column_id
                    col_map = {}  # Maps by output name
                    col_id_map = {}  # Maps by column_id (for reference resolution)
                    col_id_order = []  # Preserve column order
                    
                    if hasattr(subquery, 'column_list'):
                        for col in subquery.column_list:
                            internal_name = col.name
                            column_id = col.column_id
                            
                            col_id_order.append(column_id)  # Track order
                            
                            
                            # Check if this column has an expression
                            if column_id in cte_expr_map:
                                # Computed column - find its parents with current CTE context
                                expr = cte_expr_map[column_id]
                                parent_cols = find_parents(expr, cte_column_map)
                                # Store by both name and column_id
                                col_map[internal_name] = parent_cols
                                col_id_map[column_id] = parent_cols
                            else:
                                # Direct column reference
                                source_table = col.table_name
                                source_col = col.name
                                if source_table and source_col:
                                    parents = {ColumnEntity(source_table, source_col)}
                                    col_map[internal_name] = parents
                                    col_id_map[column_id] = parents
                    
                    # Store both mappings and column order
                    cte_column_map[cte_name] = {
                        'by_name': col_map,
                        'by_id': col_id_map,
                        'id_order': col_id_order  # Preserve column order
                    }
        
        # Recurse into child nodes - also build alias map from WithRefScan
        if hasattr(node, 'query') and node.query:
            self._build_cte_alias_map(node.query, cte_column_map)
            self._build_cte_column_map(node.query, cte_column_map)
        if hasattr(node, 'input_scan') and node.input_scan:
            self._build_cte_alias_map(node.input_scan, cte_column_map)
            self._build_cte_column_map(node.input_scan, cte_column_map)
    
    def _build_cte_alias_map(self, node: ResolvedNode, cte_column_map: dict):
        """Build alias mapping from WithRefScan.
        
        Args:
            node: Node to traverse
            cte_column_map: CTE column map to update with aliases
        """
        node_type = type(node).__name__
        
        # Handle WithRefScan - this gives us the alias mapping
        if node_type == 'ResolvedWithRefScan':
            cte_name = node.with_query_name if hasattr(node, 'with_query_name') else None
            if cte_name and cte_name in cte_column_map and hasattr(node, 'column_list'):
                
                # Get the CTE definition info
                cte_info = cte_column_map[cte_name]
                col_map_by_name = cte_info.get('by_name', {})
                col_id_map = cte_info.get('by_id', {})
                col_id_order = cte_info.get('id_order', [])  # Get original column order
                
                
                # Build alias mapping by position using original order
                for i, ref_col in enumerate(node.column_list):
                    ref_name = ref_col.name  # This is the alias used in main query
                    ref_id = ref_col.column_id  # New column ID for this reference
                    
                    
                    # Match by position to CTE internal column using original order
                    if i < len(col_id_order):
                        internal_col_id = col_id_order[i]
                        if internal_col_id in col_id_map:
                            # Add this alias to by_name mapping
                            col_map_by_name[ref_name] = col_id_map[internal_col_id]
        
        # Recurse
        if hasattr(node, 'input_scan') and node.input_scan:
            self._build_cte_alias_map(node.input_scan, cte_column_map)
        if hasattr(node, 'left_scan') and node.left_scan:
            self._build_cte_alias_map(node.left_scan, cte_column_map)
        if hasattr(node, 'right_scan') and node.right_scan:
            self._build_cte_alias_map(node.right_scan, cte_column_map)
    
    def _build_column_expr_map(self, node: ResolvedNode, column_expr_map: dict):
        """Recursively build a mapping from column_id to expression.
        
        Args:
            node: Node to traverse
            column_expr_map: Dictionary to populate with column_id -> expression mappings
        """
        # Check for expr_list (ResolvedProjectScan, etc.)
        if hasattr(node, 'expr_list'):
            for computed_col in node.expr_list:
                if hasattr(computed_col, 'column') and hasattr(computed_col, 'expr'):
                    column_id = computed_col.column.column_id
                    column_expr_map[column_id] = computed_col.expr
        
        # Handle AggregateScan - map group_by and aggregate columns
        node_type = type(node).__name__
        if node_type == 'ResolvedAggregateScan':
            # Map GROUP BY columns to their source
            if hasattr(node, 'group_by_list'):
                for group_by in node.group_by_list:
                    if hasattr(group_by, 'column') and hasattr(group_by, 'expr'):
                        column_id = group_by.column.column_id
                        column_expr_map[column_id] = group_by.expr
            
            # Map aggregate function columns
            if hasattr(node, 'aggregate_list'):
                for agg in node.aggregate_list:
                    if hasattr(agg, 'column') and hasattr(agg, 'expr'):
                        column_id = agg.column.column_id
                        column_expr_map[column_id] = agg.expr
        
        # Handle AnalyticScan (window functions)
        elif node_type == 'ResolvedAnalyticScan':
            if hasattr(node, 'function_group_list'):
                for group in node.function_group_list:
                    if hasattr(group, 'analytic_function_list'):
                        for analytic_fn in group.analytic_function_list:
                            if hasattr(analytic_fn, 'column') and hasattr(analytic_fn, 'expr'):
                                column_id = analytic_fn.column.column_id
                                column_expr_map[column_id] = analytic_fn.expr
        
        # Recurse into child nodes
        if hasattr(node, 'input_scan') and node.input_scan:
            self._build_column_expr_map(node.input_scan, column_expr_map)
        
        # Handle other scan types
        if hasattr(node, 'left_scan') and node.left_scan:
            self._build_column_expr_map(node.left_scan, column_expr_map)
        if hasattr(node, 'right_scan') and node.right_scan:
            self._build_column_expr_map(node.right_scan, column_expr_map)
        
        # Handle WITH scans
        if hasattr(node, 'with_entry_list'):
            for entry in node.with_entry_list:
                if hasattr(entry, 'with_subquery') and entry.with_subquery:
                    # Recursively build expr map for CTE subquery
                    self._build_column_expr_map(entry.with_subquery, column_expr_map)
        
        # Handle WithRefScan - map referenced CTE columns back to their definitions
        if node_type == 'ResolvedWithRefScan':
            # This references a CTE - already handled in with_entry_list above
            pass
    
    def _process_output_column(self, output_col: ResolvedOutputColumn):
        """Process an output column to extract lineage.
        
        Args:
            output_col: ResolvedOutputColumn to process
        """
        # Create target column
        target_col = ColumnEntity(self.target_table, output_col.name)
        
        # Find parent columns from the column's expression
        parent_cols = set()
        
        if output_col.column:
            col = output_col.column
            
            # Check if column has an expression (computed column)
            # For now, we'll trace back through the column reference
            # This is simplified - in reality we'd need to traverse the query tree
            if col.table_name and col.name:
                # Direct column reference
                parent_cols = {ColumnEntity(col.table_name, col.name)}
        
        lineage = ColumnLineage(
            target=target_col,
            parents=parent_cols
        )
        self.lineages.append(lineage)
    
    def default_visit(self, node: ResolvedNode):
        """Default visitor - traverse all children.
        
        Args:
            node: Any ResolvedNode
        """
        self.descend(node)


def extract_column_lineage(resolved_stmt: ResolvedStatement) -> List[ColumnLineage]:
    """Extract column-level lineage from a resolved statement.
    
    Args:
        resolved_stmt: Resolved SQL statement
        
    Returns:
        List of ColumnLineage objects, one per output column
    """
    extractor = ColumnLineageExtractor()
    extractor.visit(resolved_stmt)
    return extractor.lineages
