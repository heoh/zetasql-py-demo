"""Tests for table-level lineage extraction."""

import pytest
from zetasql.api import Analyzer
from src.zetasql_demo.lineage.models import TableEntity, TableLineage
from src.zetasql_demo.lineage.table_lineage import extract_table_lineage


# ============================================================================
# Basic SQL Statements
# ============================================================================

def test_select_from_single_table(analyzer: Analyzer):
    """Test SELECT from a single table."""
    sql = "SELECT order_id, amount FROM orders"
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage is not None
    assert lineage.target_table is None  # SELECT has no target
    assert len(lineage.source_tables) == 1
    assert TableEntity("orders") in lineage.source_tables
    assert lineage.statement_type == "QUERY"


def test_select_with_join(analyzer: Analyzer):
    """Test SELECT with JOIN."""
    sql = """
        SELECT o.order_id, c.name, o.amount
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table is None
    assert len(lineage.source_tables) == 2
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables
    assert lineage.statement_type == "QUERY"


def test_create_table_as_select(analyzer: Analyzer):
    """Test CREATE TABLE AS SELECT."""
    sql = """
        CREATE TABLE analytics.order_summary AS
        SELECT order_id, amount
        FROM orders
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("analytics.order_summary")
    assert len(lineage.source_tables) == 1
    assert TableEntity("orders") in lineage.source_tables
    assert lineage.statement_type == "CREATE_TABLE_AS_SELECT"


def test_create_view_as_select(analyzer: Analyzer):
    """Test CREATE VIEW AS SELECT."""
    sql = """
        CREATE VIEW analytics.customer_orders AS
        SELECT c.customer_id, c.name, o.order_id, o.amount
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("analytics.customer_orders")
    assert len(lineage.source_tables) == 2
    assert TableEntity("customers") in lineage.source_tables
    assert TableEntity("orders") in lineage.source_tables
    assert lineage.statement_type == "CREATE_VIEW"


def test_insert_into_table(analyzer: Analyzer):
    """Test INSERT INTO ... SELECT."""
    sql = """
        INSERT INTO orders (order_id, customer_id, amount)
        SELECT order_id, customer_id, amount
        FROM orders
        WHERE order_date > '2024-01-01'
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("orders")
    assert len(lineage.source_tables) == 1
    assert TableEntity("orders") in lineage.source_tables
    assert lineage.statement_type == "INSERT"


def test_update_table(analyzer: Analyzer):
    """Test UPDATE statement."""
    sql = """
        UPDATE orders
        SET amount = amount * 1.1
        WHERE customer_id IN (SELECT customer_id FROM customers WHERE country = 'US')
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("orders")
    # UPDATE can reference both the target table and others in WHERE clause
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables
    assert lineage.statement_type == "UPDATE"


def test_merge_statement(analyzer: Analyzer):
    """Test MERGE statement."""
    sql = """
        MERGE orders T
        USING orders S
        ON T.order_id = S.order_id
        WHEN MATCHED THEN
            UPDATE SET amount = S.amount
        WHEN NOT MATCHED THEN
            INSERT (order_id, customer_id, amount) VALUES (S.order_id, S.customer_id, S.amount)
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("orders")
    assert TableEntity("orders") in lineage.source_tables
    assert lineage.statement_type == "MERGE"


def test_delete_statement(analyzer: Analyzer):
    """Test DELETE statement."""
    sql = """
        DELETE FROM orders
        WHERE customer_id IN (SELECT customer_id FROM customers WHERE country = 'US')
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("orders")
    # DELETE can reference other tables in WHERE clause
    assert TableEntity("customers") in lineage.source_tables
    assert lineage.statement_type == "DELETE"


# ============================================================================
# Complex Queries
# ============================================================================

def test_select_with_subquery(analyzer: Analyzer):
    """Test SELECT with subquery."""
    sql = """
        SELECT order_id, amount
        FROM orders
        WHERE customer_id IN (
            SELECT customer_id 
            FROM customers 
            WHERE country = 'US'
        )
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table is None
    assert len(lineage.source_tables) == 2
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables


def test_select_with_cte(analyzer: Analyzer):
    """Test SELECT with CTE (WITH clause)."""
    sql = """
        WITH us_customers AS (
            SELECT customer_id, name
            FROM customers
            WHERE country = 'US'
        )
        SELECT o.order_id, o.amount, c.name
        FROM orders o
        JOIN us_customers c ON o.customer_id = c.customer_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table is None
    assert len(lineage.source_tables) == 2
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables


def test_nested_cte(analyzer: Analyzer):
    """Test nested CTEs."""
    sql = """
        WITH us_customers AS (
            SELECT customer_id, name
            FROM customers
            WHERE country = 'US'
        ),
        us_orders AS (
            SELECT o.order_id, o.amount, c.name
            FROM orders o
            JOIN us_customers c ON o.customer_id = c.customer_id
        )
        SELECT * FROM us_orders
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table is None
    assert len(lineage.source_tables) == 2
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables


def test_multiple_joins(analyzer: Analyzer):
    """Test query with multiple JOINs."""
    sql = """
        SELECT o.order_id, c.name, p.name AS product_name, o.amount
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN products p ON o.product_id = p.product_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table is None
    assert len(lineage.source_tables) == 3
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables
    assert TableEntity("products") in lineage.source_tables


def test_union_query(analyzer: Analyzer):
    """Test UNION query."""
    sql = """
        SELECT order_id, amount FROM orders WHERE order_date < '2024-01-01'
        UNION ALL
        SELECT order_id, amount FROM orders WHERE order_date >= '2024-01-01'
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table is None
    # Should capture the table from both sides of UNION
    assert TableEntity("orders") in lineage.source_tables


def test_create_table_as_select_with_join(analyzer: Analyzer):
    """Test CREATE TABLE AS SELECT with JOIN."""
    sql = """
        CREATE TABLE analytics.enriched_orders AS
        SELECT o.order_id, o.amount, c.name AS customer_name, p.name AS product_name
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN products p ON o.product_id = p.product_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("analytics.enriched_orders")
    assert len(lineage.source_tables) == 3
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables
    assert TableEntity("products") in lineage.source_tables


def test_create_table_as_select_with_cte(analyzer: Analyzer):
    """Test CREATE TABLE AS SELECT with CTE."""
    sql = """
        CREATE TABLE analytics.us_order_summary AS
        WITH us_customers AS (
            SELECT customer_id
            FROM customers
            WHERE country = 'US'
        )
        SELECT o.order_id, o.amount
        FROM orders o
        WHERE o.customer_id IN (SELECT customer_id FROM us_customers)
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("analytics.us_order_summary")
    assert len(lineage.source_tables) == 2
    assert TableEntity("orders") in lineage.source_tables
    assert TableEntity("customers") in lineage.source_tables


def test_insert_with_cte(analyzer: Analyzer):
    """Test INSERT with CTE."""
    sql = """
        INSERT INTO orders (order_id, customer_id, amount)
        WITH recent_orders AS (
            SELECT order_id, customer_id, amount
            FROM orders
            WHERE order_date > '2024-01-01'
        )
        SELECT * FROM recent_orders
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    
    assert lineage.target_table == TableEntity("orders")
    assert TableEntity("orders") in lineage.source_tables
