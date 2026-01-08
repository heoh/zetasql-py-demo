"""Tests for column-level lineage extraction."""

import pytest
from zetasql.api import Analyzer
from src.zetasql_demo.lineage.models import ColumnEntity, ColumnLineage
from src.zetasql_demo.lineage.column_lineage import extract_column_lineage


# ============================================================================
# Basic SELECT - Simple Projections
# ============================================================================

def test_select_simple_column(analyzer: Analyzer):
    """Test SELECT with simple column reference."""
    sql = "SELECT order_id FROM orders"
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 1
    lineage = lineages[0]
    
    # Output column has no target table (SELECT statement)
    assert lineage.target.table is None
    assert lineage.target.column == "order_id"
    
    # Parent is the source column
    assert len(lineage.parents) == 1
    parent = list(lineage.parents)[0]
    assert parent.table == "orders"
    assert parent.column == "order_id"


def test_select_multiple_columns(analyzer: Analyzer):
    """Test SELECT with multiple columns."""
    sql = "SELECT order_id, customer_id, amount FROM orders"
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    # Check each column has correct lineage
    columns = {l.target.column: l for l in lineages}
    
    assert "order_id" in columns
    assert len(columns["order_id"].parents) == 1
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "customer_id" in columns
    assert ColumnEntity("orders", "customer_id") in columns["customer_id"].parents
    
    assert "amount" in columns
    assert ColumnEntity("orders", "amount") in columns["amount"].parents


def test_select_with_alias(analyzer: Analyzer):
    """Test SELECT with column alias."""
    sql = "SELECT order_id AS id, amount AS total FROM orders"
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 2
    
    columns = {l.target.column: l for l in lineages}
    
    # Aliases become the target column names
    assert "id" in columns
    assert ColumnEntity("orders", "order_id") in columns["id"].parents
    
    assert "total" in columns
    assert ColumnEntity("orders", "amount") in columns["total"].parents


# ============================================================================
# Arithmetic and Expressions
# ============================================================================

def test_select_with_arithmetic(analyzer: Analyzer):
    """Test SELECT with arithmetic expression."""
    sql = "SELECT amount * 1.1 AS increased_amount FROM orders"
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 1
    lineage = lineages[0]
    
    assert lineage.target.column == "increased_amount"
    assert len(lineage.parents) == 1
    assert ColumnEntity("orders", "amount") in lineage.parents


def test_select_with_multiple_column_expression(analyzer: Analyzer):
    """Test SELECT with expression using multiple columns."""
    sql = "SELECT quantity * amount AS total FROM orders"
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 1
    lineage = lineages[0]
    
    assert lineage.target.column == "total"
    assert len(lineage.parents) == 2
    assert ColumnEntity("orders", "quantity") in lineage.parents
    assert ColumnEntity("orders", "amount") in lineage.parents


# ============================================================================
# Functions
# ============================================================================

def test_select_with_function(analyzer: Analyzer):
    """Test SELECT with function call."""
    sql = "SELECT UPPER(name) AS upper_name FROM customers"
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 1
    lineage = lineages[0]
    
    assert lineage.target.column == "upper_name"
    assert len(lineage.parents) == 1
    assert ColumnEntity("customers", "name") in lineage.parents


def test_select_with_aggregate(analyzer: Analyzer):
    """Test SELECT with aggregate function."""
    sql = "SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id"
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 2
    
    columns = {l.target.column: l for l in lineages}
    
    # customer_id is passed through
    assert "customer_id" in columns
    assert ColumnEntity("orders", "customer_id") in columns["customer_id"].parents
    
    # total comes from amount
    assert "total" in columns
    assert ColumnEntity("orders", "amount") in columns["total"].parents


# ============================================================================
# CASE Expressions
# ============================================================================

def test_select_with_case(analyzer: Analyzer):
    """Test SELECT with CASE expression."""
    sql = """
        SELECT 
            order_id,
            CASE 
                WHEN amount > 1000 THEN 'high'
                WHEN amount > 500 THEN 'medium'
                ELSE 'low'
            END AS category
        FROM orders
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 2
    
    columns = {l.target.column: l for l in lineages}
    
    assert "order_id" in columns
    assert "category" in columns
    # category depends on amount
    assert ColumnEntity("orders", "amount") in columns["category"].parents


# ============================================================================
# JOINs
# ============================================================================

def test_select_with_join(analyzer: Analyzer):
    """Test SELECT with JOIN."""
    sql = """
        SELECT o.order_id, c.name, o.amount
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    columns = {l.target.column: l for l in lineages}
    
    assert "order_id" in columns
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "name" in columns
    assert ColumnEntity("customers", "name") in columns["name"].parents
    
    assert "amount" in columns
    assert ColumnEntity("orders", "amount") in columns["amount"].parents


def test_select_with_join_expression(analyzer: Analyzer):
    """Test SELECT with JOIN and expressions."""
    sql = """
        SELECT 
            o.order_id,
            c.name,
            o.quantity * p.price AS total
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN products p ON o.product_id = p.product_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    columns = {l.target.column: l for l in lineages}
    
    # total depends on columns from two different tables
    assert "total" in columns
    assert ColumnEntity("orders", "quantity") in columns["total"].parents
    assert ColumnEntity("products", "price") in columns["total"].parents


# ============================================================================
# Subqueries
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
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 2
    
    columns = {l.target.column: l for l in lineages}
    
    # Output columns only depend on orders table columns
    assert "order_id" in columns
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "amount" in columns
    assert ColumnEntity("orders", "amount") in columns["amount"].parents


# ============================================================================
# CTEs
# ============================================================================

def test_select_with_cte(analyzer: Analyzer):
    """Test SELECT with CTE."""
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
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    columns = {l.target.column: l for l in lineages}
    
    assert "order_id" in columns
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "amount" in columns
    assert ColumnEntity("orders", "amount") in columns["amount"].parents
    
    # name comes from customers through CTE
    assert "name" in columns
    assert ColumnEntity("customers", "name") in columns["name"].parents


def test_select_with_cte_expression(analyzer: Analyzer):
    """Test SELECT with CTE and expressions."""
    sql = """
        WITH order_totals AS (
            SELECT customer_id, SUM(amount) AS total_amount
            FROM orders
            GROUP BY customer_id
        )
        SELECT c.name, t.total_amount
        FROM customers c
        JOIN order_totals t ON c.customer_id = t.customer_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 2
    
    columns = {l.target.column: l for l in lineages}
    
    assert "name" in columns
    assert ColumnEntity("customers", "name") in columns["name"].parents
    
    # total_amount comes from orders.amount through CTE
    assert "total_amount" in columns
    assert ColumnEntity("orders", "amount") in columns["total_amount"].parents


# ============================================================================
# Window Functions
# ============================================================================

def test_select_with_window_function(analyzer: Analyzer):
    """Test SELECT with window function."""
    sql = """
        SELECT 
            order_id,
            amount,
            SUM(amount) OVER (PARTITION BY customer_id) AS customer_total
        FROM orders
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    columns = {l.target.column: l for l in lineages}
    
    assert "order_id" in columns
    assert "amount" in columns
    
    # customer_total depends on amount
    assert "customer_total" in columns
    assert ColumnEntity("orders", "amount") in columns["customer_total"].parents


# ============================================================================
# CREATE TABLE AS SELECT
# ============================================================================

def test_create_table_as_select(analyzer: Analyzer):
    """Test CREATE TABLE AS SELECT."""
    sql = """
        CREATE TABLE analytics.order_summary AS
        SELECT order_id, amount
        FROM orders
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 2
    
    columns = {l.target.column: l for l in lineages}
    
    # Target columns have table name
    for lineage in lineages:
        assert lineage.target.table == "analytics.order_summary"
    
    assert "order_id" in columns
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "amount" in columns
    assert ColumnEntity("orders", "amount") in columns["amount"].parents


def test_create_table_as_select_with_expressions(analyzer: Analyzer):
    """Test CREATE TABLE AS SELECT with expressions."""
    sql = """
        CREATE TABLE analytics.enriched_orders AS
        SELECT 
            o.order_id,
            c.name AS customer_name,
            o.quantity * p.price AS total
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN products p ON o.product_id = p.product_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    columns = {l.target.column: l for l in lineages}
    
    for lineage in lineages:
        assert lineage.target.table == "analytics.enriched_orders"
    
    assert "order_id" in columns
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "customer_name" in columns
    assert ColumnEntity("customers", "name") in columns["customer_name"].parents
    
    assert "total" in columns
    assert ColumnEntity("orders", "quantity") in columns["total"].parents
    assert ColumnEntity("products", "price") in columns["total"].parents


# ============================================================================
# CREATE VIEW
# ============================================================================

def test_create_view(analyzer: Analyzer):
    """Test CREATE VIEW."""
    sql = """
        CREATE VIEW analytics.customer_orders AS
        SELECT c.customer_id, c.name, o.order_id, o.amount
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 4
    
    columns = {l.target.column: l for l in lineages}
    
    for lineage in lineages:
        assert lineage.target.table == "analytics.customer_orders"
    
    assert "customer_id" in columns
    assert ColumnEntity("customers", "customer_id") in columns["customer_id"].parents
    
    assert "name" in columns
    assert ColumnEntity("customers", "name") in columns["name"].parents
    
    assert "order_id" in columns
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "amount" in columns
    assert ColumnEntity("orders", "amount") in columns["amount"].parents


# ============================================================================
# INSERT
# ============================================================================

def test_insert_select(analyzer: Analyzer):
    """Test INSERT with SELECT."""
    sql = """
        INSERT INTO orders (order_id, customer_id, amount)
        SELECT order_id, customer_id, amount * 2
        FROM orders
        WHERE order_date > '2024-01-01'
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    columns = {l.target.column: l for l in lineages}
    
    for lineage in lineages:
        assert lineage.target.table == "orders"
    
    assert "order_id" in columns
    assert ColumnEntity("orders", "order_id") in columns["order_id"].parents
    
    assert "customer_id" in columns
    assert ColumnEntity("orders", "customer_id") in columns["customer_id"].parents
    
    # amount comes from expression
    assert "amount" in columns
    assert ColumnEntity("orders", "amount") in columns["amount"].parents


# ============================================================================
# Complex Expressions
# ============================================================================

def test_complex_nested_expression(analyzer: Analyzer):
    """Test complex nested expressions."""
    sql = """
        SELECT 
            order_id,
            CASE 
                WHEN amount > 1000 THEN amount * 0.9
                ELSE amount
            END AS discounted_amount,
            COALESCE(quantity * amount, 0) AS total
        FROM orders
    """
    
    stmt = analyzer.analyze_statement(sql)
    lineages = extract_column_lineage(stmt)
    
    assert len(lineages) == 3
    
    columns = {l.target.column: l for l in lineages}
    
    assert "order_id" in columns
    
    # discounted_amount depends on amount
    assert "discounted_amount" in columns
    assert ColumnEntity("orders", "amount") in columns["discounted_amount"].parents
    
    # total depends on quantity and amount
    assert "total" in columns
    assert ColumnEntity("orders", "quantity") in columns["total"].parents
    assert ColumnEntity("orders", "amount") in columns["total"].parents
