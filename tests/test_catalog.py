"""Tests for sample catalog creation.

Tests verify that the sample catalog is properly configured with
BigQuery-style tables (project.dataset.table naming) and builtin functions.
"""

import pytest
from zetasql.types import SimpleCatalog, TypeKind


def test_create_sample_catalog_returns_catalog():
    """Test that create_sample_catalog returns a SimpleCatalog instance."""
    from zetasql_demo.catalog import create_sample_catalog
    
    catalog = create_sample_catalog()
    
    assert catalog is not None
    assert isinstance(catalog, SimpleCatalog)


def test_catalog_has_expected_tables():
    """Test that catalog contains all expected sample tables."""
    from zetasql_demo.catalog import create_sample_catalog
    
    catalog = create_sample_catalog()
    
    # Expected tables with BigQuery naming: project.dataset.table
    expected_tables = [
        "project1.dataset1.orders",
        "project1.dataset1.customers",
        "project1.dataset1.products",
        "project1.dataset1.order_items",
    ]
    
    # Get table names from catalog
    table_names = [table.name for table in catalog.table]
    
    for expected_table in expected_tables:
        assert expected_table in table_names, f"Table {expected_table} not found in catalog"


def test_orders_table_has_correct_columns():
    """Test that orders table has expected columns with correct types."""
    from zetasql_demo.catalog import create_sample_catalog
    
    catalog = create_sample_catalog()
    
    # Find orders table
    orders_table = None
    for table in catalog.table:
        if table.name == "project1.dataset1.orders":
            orders_table = table
            break
    
    assert orders_table is not None, "Orders table not found"
    
    # Expected columns: order_id, customer_id, amount, order_date
    column_names = [col.name for col in orders_table.column]
    
    assert "order_id" in column_names
    assert "customer_id" in column_names
    assert "amount" in column_names
    assert "order_date" in column_names
    
    # Check types
    columns_by_name = {col.name: col for col in orders_table.column}
    
    assert columns_by_name["order_id"].type.type_kind == TypeKind.TYPE_INT64
    assert columns_by_name["customer_id"].type.type_kind == TypeKind.TYPE_INT64
    assert columns_by_name["amount"].type.type_kind == TypeKind.TYPE_DOUBLE
    assert columns_by_name["order_date"].type.type_kind == TypeKind.TYPE_DATE


def test_customers_table_has_correct_columns():
    """Test that customers table has expected columns with correct types."""
    from zetasql_demo.catalog import create_sample_catalog
    
    catalog = create_sample_catalog()
    
    # Find customers table
    customers_table = None
    for table in catalog.table:
        if table.name == "project1.dataset1.customers":
            customers_table = table
            break
    
    assert customers_table is not None, "Customers table not found"
    
    # Expected columns: customer_id, name, email, region
    column_names = [col.name for col in customers_table.column]
    
    assert "customer_id" in column_names
    assert "name" in column_names
    assert "email" in column_names
    assert "region" in column_names
    
    # Check types
    columns_by_name = {col.name: col for col in customers_table.column}
    
    assert columns_by_name["customer_id"].type.type_kind == TypeKind.TYPE_INT64
    assert columns_by_name["name"].type.type_kind == TypeKind.TYPE_STRING
    assert columns_by_name["email"].type.type_kind == TypeKind.TYPE_STRING
    assert columns_by_name["region"].type.type_kind == TypeKind.TYPE_STRING


def test_products_table_has_correct_columns():
    """Test that products table has expected columns with correct types."""
    from zetasql_demo.catalog import create_sample_catalog
    
    catalog = create_sample_catalog()
    
    # Find products table
    products_table = None
    for table in catalog.table:
        if table.name == "project1.dataset1.products":
            products_table = table
            break
    
    assert products_table is not None, "Products table not found"
    
    # Expected columns: product_id, name, price, category
    column_names = [col.name for col in products_table.column]
    
    assert "product_id" in column_names
    assert "name" in column_names
    assert "price" in column_names
    assert "category" in column_names
    
    # Check types
    columns_by_name = {col.name: col for col in products_table.column}
    
    assert columns_by_name["product_id"].type.type_kind == TypeKind.TYPE_INT64
    assert columns_by_name["name"].type.type_kind == TypeKind.TYPE_STRING
    assert columns_by_name["price"].type.type_kind == TypeKind.TYPE_DOUBLE
    assert columns_by_name["category"].type.type_kind == TypeKind.TYPE_STRING


def test_order_items_table_has_correct_columns():
    """Test that order_items table has expected columns with correct types."""
    from zetasql_demo.catalog import create_sample_catalog
    
    catalog = create_sample_catalog()
    
    # Find order_items table
    order_items_table = None
    for table in catalog.table:
        if table.name == "project1.dataset1.order_items":
            order_items_table = table
            break
    
    assert order_items_table is not None, "Order_items table not found"
    
    # Expected columns: order_id, product_id, quantity, price
    column_names = [col.name for col in order_items_table.column]
    
    assert "order_id" in column_names
    assert "product_id" in column_names
    assert "quantity" in column_names
    assert "price" in column_names
    
    # Check types
    columns_by_name = {col.name: col for col in order_items_table.column}
    
    assert columns_by_name["order_id"].type.type_kind == TypeKind.TYPE_INT64
    assert columns_by_name["product_id"].type.type_kind == TypeKind.TYPE_INT64
    assert columns_by_name["quantity"].type.type_kind == TypeKind.TYPE_INT64
    assert columns_by_name["price"].type.type_kind == TypeKind.TYPE_DOUBLE


def test_catalog_has_builtin_functions():
    """Test that catalog includes builtin functions."""
    from zetasql_demo.catalog import create_sample_catalog
    
    catalog = create_sample_catalog()
    
    # Check that builtin_function_options is configured
    assert catalog.builtin_function_options is not None


def test_analyzer_can_analyze_simple_query(analyzer):
    """Integration test: verify analyzer can analyze a simple query using the catalog."""
    # Simple SELECT query with backticks for BigQuery-style table names
    sql = "SELECT order_id, amount FROM `project1.dataset1.orders`"
    
    stmt = analyzer.analyze_statement(sql)
    
    assert stmt is not None
    # Should have 2 output columns
    assert len(stmt.output_column_list) == 2
    assert stmt.output_column_list[0].name == "order_id"
    assert stmt.output_column_list[1].name == "amount"


def test_analyzer_can_analyze_join_query(analyzer):
    """Integration test: verify analyzer can analyze JOIN queries."""
    sql = """
        SELECT 
            o.order_id,
            c.name,
            o.amount
        FROM `project1.dataset1.orders` o
        JOIN `project1.dataset1.customers` c
            ON o.customer_id = c.customer_id
    """
    
    stmt = analyzer.analyze_statement(sql)
    
    assert stmt is not None
    assert len(stmt.output_column_list) == 3
