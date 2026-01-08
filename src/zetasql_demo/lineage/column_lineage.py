"""Column-level lineage extraction using ResolvedNodeVisitor.

Port of Java classes from zetasql-toolkit:
- ExpressionParentFinder.java
- ParentColumnFinder.java
- ColumnLineageExtractor.java
"""

from collections import deque
from typing import Dict, List, Optional, Set

from zetasql.api import ResolvedNodeVisitor
from zetasql.types import ResolvedColumn, ResolvedExpr, ResolvedStatement

from .models import ColumnEntity, ColumnLineage


def make_column_key(column: ResolvedColumn) -> str:
    """Generate unique key for a ResolvedColumn.
    
    Args:
        column: ResolvedColumn instance
        
    Returns:
        Unique string key in format "table.name#id"
    """
    return f"{column.table_name}.{column.name}#{column.column_id}"


def expand_struct_column(column: ResolvedColumn) -> List[ResolvedColumn]:
    """Recursively expand STRUCT columns into their fields.
    
    Port of ParentColumnFinder.expandColumn() from Java.
    
    Args:
        column: ResolvedColumn to expand
        
    Returns:
        List containing the column itself and all its STRUCT fields recursively
        
    Example:
        >>> # column: user_struct STRUCT<name STRING, address STRUCT<city STRING>>
        >>> expanded = expand_struct_column(column)
        >>> # Returns: [user_struct, user_struct.name, user_struct.address, 
        >>> #           user_struct.address.city]
    """
    result = [column]
    
    column_type = column.type
    if column_type.is_struct():
        struct_type = column_type.as_struct()
        if struct_type is not None:
            for field in struct_type.field:
                field_column = ResolvedColumn(
                    column_id=column.column_id,
                    table_name=column.table_name,
                    name=f"{column.name}.{field.field_name}",
                    type_=field.field_type
                )
                # Recursively expand nested STRUCTs
                result.extend(expand_struct_column(field_column))
    
    return result


class ExpressionParentFinder(ResolvedNodeVisitor):
    """Finds the direct parent columns of a ResolvedExpr.
    
    Port of ExpressionParentFinder.java from zetasql-toolkit.
    
    Traverses an expression to find all columns it directly references.
    Special handling for functions like CASE, IF, NULLIF where not all
    arguments contribute to the output value.
    
    Example:
        >>> # Expression: UPPER(CONCAT(col1, col2))
        >>> parents = ExpressionParentFinder.find_direct_parents(expression)
        >>> # Returns: [col1, col2]
    """
    
    def __init__(self):
        super().__init__()
        self.result: List[ResolvedColumn] = []
    
    @staticmethod
    def find_direct_parents(expression: ResolvedExpr) -> List[ResolvedColumn]:
        """Find direct parent columns for an expression.
        
        Args:
            expression: ResolvedExpr to analyze
            
        Returns:
            List of ResolvedColumns directly referenced by the expression
        """
        finder = ExpressionParentFinder()
        finder.visit(expression)
        return finder.result
    
    def visit_ResolvedColumnRef(self, node):
        """Visit column reference nodes.
        
        Args:
            node: ResolvedColumnRef node
        """
        self.result.append(node.column)
    
    def visit_ResolvedWithExpr(self, node):
        """Visit WITH expression nodes.
        
        Args:
            node: ResolvedWithExpr node
        """
        self.visit(node.expr)
    
    def visit_ResolvedSubqueryExpr(self, node):
        """Visit subquery expression nodes.
        
        Only SCALAR and ARRAY subqueries contribute columns.
        EXISTS/IN subqueries do not contribute to output.
        
        Args:
            node: ResolvedSubqueryExpr node
        """
        # SCALAR = 0, ARRAY = 1, EXISTS = 2, IN = 3
        if node.subquery_type in (0, 1):  # SCALAR or ARRAY
            subquery = node.subquery
            if subquery.column_list:
                subquery_output_column = subquery.column_list[0]
                self.result.append(subquery_output_column)
    
    def _visit_function_call_base(self, node):
        """Visit function call nodes with special handling for CASE/IF/NULLIF.
        
        Args:
            node: ResolvedFunctionCall or aggregate/analytic function node
        """
        function = node.function
        arguments = node.argument_list
        num_args = len(arguments)
        
        # Determine which arguments contribute to output
        expressions_to_visit = []
        function_name = function.name.lower()
        
        if function_name == "$case_no_value":
            # CASE WHEN cond1 THEN val1 WHEN cond2 THEN val2 ELSE val3
            # Keep odd indices (WHEN values) + last (ELSE)
            # args: [cond1, val1, cond2, val2, val3]
            expressions_to_visit = [
                arguments[i] for i in range(num_args)
                if i % 2 == 1 or i == num_args - 1
            ]
        elif function_name == "$case_with_value":
            # CASE expr WHEN val1 THEN result1 WHEN val2 THEN result2 ELSE result3
            # Keep even indices except first (skip CASE expr) + last (ELSE)
            # args: [expr, val1, result1, val2, result2, result3]
            expressions_to_visit = [
                arguments[i] for i in range(num_args)
                if (i != 0 and i % 2 == 0) or i == num_args - 1
            ]
        elif function_name == "if":
            # IF(condition, true_case, false_case)
            # Skip first argument (condition)
            expressions_to_visit = arguments[1:]
        elif function_name == "nullif":
            # NULLIF(value, null_value)
            # Keep only first argument (the value)
            expressions_to_visit = [arguments[0]] if arguments else []
        else:
            # Default: all arguments contribute
            expressions_to_visit = arguments
        
        # Visit selected expressions
        for expr in expressions_to_visit:
            self.visit(expr)
    
    def visit_ResolvedFunctionCall(self, node):
        """Visit function call nodes.
        
        Args:
            node: ResolvedFunctionCall node
        """
        self._visit_function_call_base(node)
    
    def visit_ResolvedAggregateFunctionCall(self, node):
        """Visit aggregate function call nodes.
        
        Args:
            node: ResolvedAggregateFunctionCall node
        """
        self._visit_function_call_base(node)
    
    def visit_ResolvedAnalyticFunctionCall(self, node):
        """Visit analytic function call nodes.
        
        Args:
            node: ResolvedAnalyticFunctionCall node
        """
        self._visit_function_call_base(node)
    
    def visit_ResolvedMakeStruct(self, node):
        """Visit STRUCT construction nodes.
        
        Args:
            node: ResolvedMakeStruct node
        """
        for field_expr in node.field_list:
            self.visit(field_expr)
    
    def visit_ResolvedGetStructField(self, node):
        """Visit STRUCT field access nodes.
        
        Args:
            node: ResolvedGetStructField node
        """
        from zetasql.types import ResolvedMakeStruct
        
        struct_expression = node.expr
        struct_type = struct_expression.type.as_struct()
        accessed_field_index = node.field_idx
        accessed_field_name = struct_type.field[accessed_field_index].name
        
        # Check if we're accessing a field from a STRUCT literal
        if isinstance(struct_expression, ResolvedMakeStruct):
            # STRUCT literal: only consider the accessed field's parents
            make_struct = struct_expression
            make_struct_type = make_struct.type.as_struct()
            num_fields = len(make_struct_type.field)
            
            # Find the field index by name
            field_index = None
            for i in range(num_fields):
                if make_struct_type.field[i].name == accessed_field_name:
                    field_index = i
                    break
            
            if field_index is not None:
                field_expression = make_struct.field_list[field_index]
                parent_columns = ExpressionParentFinder.find_direct_parents(field_expression)
                self.result.extend(parent_columns)
        else:
            # Regular column: visit and append field name
            self.visit(struct_expression)
            
            if self.result:
                struct_column = self.result.pop()
                parent_column = ResolvedColumn(
                    column_id=struct_column.column_id,
                    table_name=struct_column.table_name,
                    name=f"{struct_column.name}.{accessed_field_name}",
                    type_=node.type
                )
                self.result.append(parent_column)
    
    def visit_ResolvedCast(self, node):
        """Visit CAST expression nodes.
        
        Args:
            node: ResolvedCast node
        """
        self.visit(node.expr)


class ParentColumnFinder(ResolvedNodeVisitor):
    """Finds terminal parent columns for columns and expressions.
    
    Port of ParentColumnFinder.java from zetasql-toolkit.
    
    Terminal parents are columns that read directly from a table.
    Uses BFS to traverse the parent chain from computed columns back to
    table columns.
    
    Attributes:
        columns_to_parents: Map of column key -> direct parent columns
        terminal_columns: Set of column keys that are terminal (from tables)
        with_entry_scopes: Stack of WITH entry scopes for CTE resolution
        columns_being_computed: Stack tracking nested computed columns
    
    Example:
        >>> # Query: SELECT UPPER(name) AS upper_name FROM users
        >>> parents = ParentColumnFinder.find_parents_for_column(stmt, upper_name_column)
        >>> # Returns: [users.name]
    """
    
    def __init__(self):
        super().__init__()
        self.columns_to_parents: Dict[str, List[ResolvedColumn]] = {}
        self.terminal_columns: Set[str] = set()
        self.with_entry_scopes: List[List] = []  # Stack of WITH entries
        self.columns_being_computed: List[ResolvedColumn] = []  # Stack
    
    @staticmethod
    def find_parents_for_column(
        statement: ResolvedStatement, 
        column: ResolvedColumn
    ) -> List[ResolvedColumn]:
        """Find terminal parents for a column.
        
        Args:
            statement: ResolvedStatement containing the column
            column: ResolvedColumn to find parents for
            
        Returns:
            List of terminal parent ResolvedColumns
        """
        finder = ParentColumnFinder()
        return finder._find_impl(statement, column)
    
    @staticmethod
    def find_parents_for_expression(
        statement: ResolvedStatement,
        expression: ResolvedExpr
    ) -> List[ResolvedColumn]:
        """Find terminal parents for an expression.
        
        Args:
            statement: ResolvedStatement containing the expression
            expression: ResolvedExpr to find parents for
            
        Returns:
            List of terminal parent ResolvedColumns
        """
        # Find direct parents of the expression
        parents_referenced = ExpressionParentFinder.find_direct_parents(expression)
        
        # Find terminal parents of each direct parent
        result = []
        for parent in parents_referenced:
            terminal_parents = ParentColumnFinder.find_parents_for_column(statement, parent)
            result.extend(terminal_parents)
        
        return result
    
    def _find_impl(
        self, 
        container_node: ResolvedStatement, 
        column: ResolvedColumn
    ) -> List[ResolvedColumn]:
        """Implementation of BFS parent finding.
        
        Args:
            container_node: AST node to traverse
            column: Column to find parents for
            
        Returns:
            List of terminal parent columns
        """
        # Step 1: Traverse AST to populate columns_to_parents map
        self.visit(container_node)
        
        # Step 2: BFS to find terminal parents
        result = []
        resolution_queue = deque([column])
        
        while resolution_queue:
            current_column = resolution_queue.popleft()
            current_key = make_column_key(current_column)
            parents = self._get_parents_of_column(current_column)
            
            if not parents and current_key in self.terminal_columns:
                # Terminal column found
                result.append(current_column)
            else:
                # Continue traversal
                resolution_queue.extend(parents)
        
        return result
    
    def _get_parents_of_column(self, column: ResolvedColumn) -> List[ResolvedColumn]:
        """Get direct parents of a column from the map.
        
        Args:
            column: ResolvedColumn to look up
            
        Returns:
            List of direct parent columns
        """
        key = make_column_key(column)
        return self.columns_to_parents.get(key, [])
    
    def _add_parents_to_column(
        self, 
        column: ResolvedColumn, 
        new_parents: List[ResolvedColumn]
    ):
        """Add parent columns to a column's parent list.
        
        Args:
            column: Target column
            new_parents: Parent columns to add
        """
        key = make_column_key(column)
        if key not in self.columns_to_parents:
            self.columns_to_parents[key] = []
        self.columns_to_parents[key].extend(new_parents)
    
    def _add_parent_to_column(
        self, 
        column: ResolvedColumn, 
        new_parent: ResolvedColumn
    ):
        """Add a single parent column to a column's parent list.
        
        Args:
            column: Target column
            new_parent: Parent column to add
        """
        self._add_parents_to_column(column, [new_parent])
    
    def _register_terminal_columns(self, new_terminal_columns: List[ResolvedColumn]):
        """Register columns as terminal (from tables).
        
        Expands STRUCT columns to include all fields.
        
        Args:
            new_terminal_columns: Columns to register as terminal
        """
        for column in new_terminal_columns:
            expanded = expand_struct_column(column)
            for expanded_col in expanded:
                key = make_column_key(expanded_col)
                self.terminal_columns.add(key)
    
    def _expand_make_struct(self, target_column: ResolvedColumn, make_struct):
        """Recursively expand MakeStruct to register field parent relationships.
        
        Args:
            target_column: The STRUCT column being computed
            make_struct: ResolvedMakeStruct node
        """
        struct_type = make_struct.type.as_struct()
        num_fields = len(struct_type.field)
        
        for i in range(num_fields):
            field = struct_type.field[i]
            field_expression = make_struct.field_list[i]
            field_column = ResolvedColumn(
                column_id=target_column.column_id,
                table_name=target_column.table_name,
                name=f"{target_column.name}.{field.field_name}",
                type_=field_expression.type
            )
            
            self.columns_being_computed.append(field_column)
            expression_parents = ExpressionParentFinder.find_direct_parents(field_expression)
            for col_being_computed in self.columns_being_computed:
                self._add_parents_to_column(col_being_computed, expression_parents)
            self.columns_being_computed.pop()
            
            # Recursively handle nested STRUCTs
            from zetasql.types import ResolvedMakeStruct
            if isinstance(field_expression, ResolvedMakeStruct):
                self._expand_make_struct(field_column, field_expression)
    
    def visit_ResolvedComputedColumn(self, node):
        """Visit computed column nodes.
        
        Registers the column and its direct parents in the map.
        
        Args:
            node: ResolvedComputedColumn node
        """
        column = node.column
        expression = node.expr
        
        self.columns_being_computed.append(column)
        
        # Special handling for STRUCT construction
        from zetasql.types import ResolvedMakeStruct
        if isinstance(expression, ResolvedMakeStruct):
            self._expand_make_struct(column, expression)
        else:
            expression_parents = ExpressionParentFinder.find_direct_parents(expression)
            for col_being_computed in self.columns_being_computed:
                self._add_parents_to_column(col_being_computed, expression_parents)
        
        self.columns_being_computed.pop()
    
    def visit_ResolvedTableScan(self, node):
        """Visit table scan nodes.
        
        Registers table columns as terminal.
        
        Args:
            node: ResolvedTableScan node
        """
        self._register_terminal_columns(node.column_list)
        self.descend(node)
    
    def visit_ResolvedTVFScan(self, node):
        """Visit TVF (table-valued function) scan nodes.
        
        Args:
            node: ResolvedTVFScan node
        """
        self._register_terminal_columns(node.column_list)
        self.descend(node)
    
    def visit_ResolvedWithScan(self, node):
        """Visit WITH (CTE) scan nodes.
        
        Pushes WITH entries onto scope stack for resolution.
        
        Args:
            node: ResolvedWithScan node
        """
        # Push WITH entries to scope stack
        self.with_entry_scopes.append(node.with_entry_list)
        
        # Visit WITH entries and main query
        for with_entry in node.with_entry_list:
            self.visit(with_entry)
        self.visit(node.query)
        
        # Pop scope when exiting WITH
        self.with_entry_scopes.pop()
    
    def _find_in_scope_with_entry_by_name(self, name: str) -> Optional:
        """Find a WITH entry by name in the current scope stack.
        
        Args:
            name: WITH query name to find
            
        Returns:
            ResolvedWithEntry if found, None otherwise
        """
        # Traverse scope stack top-to-bottom
        for i in range(len(self.with_entry_scopes) - 1, -1, -1):
            in_scope_entries = self.with_entry_scopes[i]
            for with_entry in in_scope_entries:
                if with_entry.with_query_name.lower() == name.lower():
                    return with_entry
        return None
    
    def visit_ResolvedWithRefScan(self, node):
        """Visit WITH reference scan nodes.
        
        Resolves references to CTEs by mapping columns 1:1.
        
        Args:
            node: ResolvedWithRefScan node
        """
        # Find matching WITH entry
        with_entry = self._find_in_scope_with_entry_by_name(node.with_query_name)
        
        if with_entry is None:
            # Should not happen in valid queries
            return
        
        # Map columns 1:1 between WITH ref and WITH entry
        # Also expand STRUCT fields
        for i in range(len(node.column_list)):
            with_ref_column = node.column_list[i]
            matching_with_entry_column = with_entry.with_subquery.column_list[i]
            
            expanded_ref = expand_struct_column(with_ref_column)
            expanded_entry = expand_struct_column(matching_with_entry_column)
            
            for j in range(len(expanded_ref)):
                self._add_parent_to_column(expanded_ref[j], expanded_entry[j])
    
    def visit_ResolvedArrayScan(self, node):
        """Visit ARRAY scan (UNNEST) nodes.
        
        Args:
            node: ResolvedArrayScan node
        """
        element_column = node.element_column
        self.columns_being_computed.append(element_column)
        self.visit(node.array_expr)
        self.columns_being_computed.pop()
        
        if node.input_scan is not None:
            self.visit(node.input_scan)
    
    def visit_ResolvedSetOperationScan(self, node):
        """Visit set operation (UNION, INTERSECT, EXCEPT) scan nodes.
        
        Maps output columns to corresponding columns from each input.
        
        Args:
            node: ResolvedSetOperationScan node
        """
        generated_columns = node.column_list
        set_operation_items = node.input_item_list
        
        # For each output column, collect corresponding columns from all inputs
        for i in range(len(generated_columns)):
            generated_column = generated_columns[i]
            parent_columns = [
                item.output_column_list[i]
                for item in set_operation_items
            ]
            self._add_parents_to_column(generated_column, parent_columns)
        
        # Visit input scans
        for item in set_operation_items:
            self.visit(item.scan)


class ColumnLineageExtractor:
    """Extracts column-level lineage from SQL statements.
    
    Port of ColumnLineageExtractor.java from zetasql-toolkit.
    
    Supports:
    - CREATE TABLE AS SELECT
    - CREATE VIEW
    - SELECT (query statements)
    - INSERT
    - UPDATE
    - MERGE
    
    Example:
        >>> # CREATE TABLE result AS SELECT UPPER(name) AS upper_name FROM users
        >>> lineages = ColumnLineageExtractor.extract(analyzed_statement)
        >>> # Returns: {ColumnLineage(
        >>> #   target=ColumnEntity("result", "upper_name"),
        >>> #   parents={ColumnEntity("users", "name")}
        >>> # )}
    """
    
    @staticmethod
    def extract(statement: ResolvedStatement) -> Set[ColumnLineage]:
        """Extract column lineage from a statement.
        
        Args:
            statement: Analyzed ResolvedStatement
            
        Returns:
            Set of ColumnLineage objects
        """
        # Use isinstance to check statement type
        from zetasql.types import (
            ResolvedCreateTableAsSelectStmt,
            ResolvedCreateViewStmt,
            ResolvedQueryStmt,
            ResolvedInsertStmt,
            ResolvedUpdateStmt,
            ResolvedMergeStmt,
        )
        
        if isinstance(statement, ResolvedCreateTableAsSelectStmt):
            return ColumnLineageExtractor._extract_for_create_table_as_select(statement)
        elif isinstance(statement, ResolvedCreateViewStmt):
            return ColumnLineageExtractor._extract_for_create_view(statement)
        elif isinstance(statement, ResolvedQueryStmt):
            return ColumnLineageExtractor._extract_for_query_stmt(statement)
        elif isinstance(statement, ResolvedInsertStmt):
            return ColumnLineageExtractor._extract_for_insert(statement)
        elif isinstance(statement, ResolvedUpdateStmt):
            return ColumnLineageExtractor._extract_for_update(statement)
        elif isinstance(statement, ResolvedMergeStmt):
            return ColumnLineageExtractor._extract_for_merge(statement)
        else:
            # Unsupported statement type
            return set()
    
    @staticmethod
    def _extract_for_create_table_as_select(stmt) -> Set[ColumnLineage]:
        """Extract lineage from CREATE TABLE AS SELECT.
        
        Args:
            stmt: ResolvedCreateTableAsSelectStmt
            
        Returns:
            Set of ColumnLineage objects
        """
        result = set()
        target_table = ".".join(stmt.name_path)
        
        for output_column in stmt.output_column_list:
            target_column_name = output_column.name
            target_entity = ColumnEntity(target_table, target_column_name)
            
            # Find terminal parents - output_column.column is the actual ResolvedColumn
            terminal_parents = ParentColumnFinder.find_parents_for_column(stmt, output_column.column)
            parent_entities = {
                ColumnEntity.from_resolved_column(parent)
                for parent in terminal_parents
            }
            
            result.add(ColumnLineage(target=target_entity, parents=parent_entities))
        
        return result
    
    @staticmethod
    def _extract_for_create_view(stmt) -> Set[ColumnLineage]:
        """Extract lineage from CREATE VIEW.
        
        Args:
            stmt: ResolvedCreateViewStmt
            
        Returns:
            Set of ColumnLineage objects
        """
        result = set()
        target_table = ".".join(stmt.name_path)
        
        for output_column in stmt.output_column_list:
            target_column_name = output_column.name
            target_entity = ColumnEntity(target_table, target_column_name)
            
            terminal_parents = ParentColumnFinder.find_parents_for_column(stmt, output_column.column)
            parent_entities = {
                ColumnEntity.from_resolved_column(parent)
                for parent in terminal_parents
            }
            
            result.add(ColumnLineage(target=target_entity, parents=parent_entities))
        
        return result
    
    @staticmethod
    def _extract_for_query_stmt(stmt) -> Set[ColumnLineage]:
        """Extract lineage from SELECT query statement.
        
        Args:
            stmt: ResolvedQueryStmt
            
        Returns:
            Set of ColumnLineage objects
        """
        result = set()
        # For SELECT, target table is empty string
        target_table = ""
        
        query = stmt.query
        for output_column in query.column_list:
            target_column_name = output_column.name
            target_entity = ColumnEntity(target_table, target_column_name)
            
            terminal_parents = ParentColumnFinder.find_parents_for_column(stmt, output_column)
            parent_entities = {
                ColumnEntity.from_resolved_column(parent)
                for parent in terminal_parents
            }
            
            result.add(ColumnLineage(target=target_entity, parents=parent_entities))
        
        return result
    
    @staticmethod
    def _extract_for_insert(stmt) -> Set[ColumnLineage]:
        """Extract lineage from INSERT statement.
        
        Args:
            stmt: ResolvedInsertStmt
            
        Returns:
            Set of ColumnLineage objects
        """
        result = set()
        target_table = stmt.table_scan.table.name
        
        # Map insert columns to query columns
        insert_columns = stmt.insert_column_list
        
        if stmt.query is not None:
            query_columns = stmt.query.column_list
            
            for i in range(len(insert_columns)):
                insert_column = insert_columns[i]
                query_column = query_columns[i]
                
                target_entity = ColumnEntity(target_table, insert_column.name)
                terminal_parents = ParentColumnFinder.find_parents_for_column(stmt, query_column)
                parent_entities = {
                    ColumnEntity.from_resolved_column(parent)
                    for parent in terminal_parents
                }
                
                result.add(ColumnLineage(target=target_entity, parents=parent_entities))
        
        return result
    
    @staticmethod
    def _extract_for_update(stmt) -> Set[ColumnLineage]:
        """Extract lineage from UPDATE statement.
        
        Args:
            stmt: ResolvedUpdateStmt
            
        Returns:
            Set of ColumnLineage objects
        """
        result = set()
        target_table = stmt.table_scan.table.name
        
        # Process UPDATE SET items
        for update_item in stmt.update_item_list:
            target_column_ref = update_item.target
            # target is a ResolvedColumnRef, get the actual column
            target_column = target_column_ref.column
            target_entity = ColumnEntity(target_table, target_column.name)
            
            # Find parents from the SET expression
            if update_item.set_value is not None:
                terminal_parents = ParentColumnFinder.find_parents_for_expression(
                    stmt, 
                    update_item.set_value.value
                )
                parent_entities = {
                    ColumnEntity.from_resolved_column(parent)
                    for parent in terminal_parents
                }
                
                result.add(ColumnLineage(target=target_entity, parents=parent_entities))
        
        return result
    
    @staticmethod
    def _extract_for_merge(stmt) -> Set[ColumnLineage]:
        """Extract lineage from MERGE statement.
        
        Args:
            stmt: ResolvedMergeStmt
            
        Returns:
            Set of ColumnLineage objects
        """
        result = set()
        target_table = stmt.table_scan.table.name
        
        # Process WHEN clauses
        for when_clause in stmt.when_clause_list:
            # MATCHED UPDATE
            if when_clause.action_type == 1:  # UPDATE
                if hasattr(when_clause, 'update_item_list'):
                    for update_item in when_clause.update_item_list:
                        target_column_ref = update_item.target
                        # target is a ResolvedColumnRef, get the actual column
                        target_column = target_column_ref.column
                        target_entity = ColumnEntity(target_table, target_column.name)
                        
                        if update_item.set_value is not None:
                            terminal_parents = ParentColumnFinder.find_parents_for_expression(
                                stmt,
                                update_item.set_value.value
                            )
                            parent_entities = {
                                ColumnEntity.from_resolved_column(parent)
                                for parent in terminal_parents
                            }
                            
                            result.add(ColumnLineage(target=target_entity, parents=parent_entities))
            
            # NOT MATCHED INSERT
            elif when_clause.action_type == 0:  # INSERT
                if hasattr(when_clause, 'insert_column_list') and \
                   hasattr(when_clause, 'insert_row'):
                    insert_columns = when_clause.insert_column_list
                    insert_row = when_clause.insert_row
                    
                    for i, insert_column in enumerate(insert_columns):
                        target_entity = ColumnEntity(target_table, insert_column.name)
                        
                        if i < len(insert_row.value_list):
                            value_expr = insert_row.value_list[i]
                            terminal_parents = ParentColumnFinder.find_parents_for_expression(
                                stmt,
                                value_expr
                            )
                            parent_entities = {
                                ColumnEntity.from_resolved_column(parent)
                                for parent in terminal_parents
                            }
                            
                            result.add(ColumnLineage(target=target_entity, parents=parent_entities))
        
        return result
