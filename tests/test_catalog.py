"""Tests for sample catalog creation."""

import pytest
from zetasql.types import SimpleCatalog


def test_sample_catalog_creation(sample_catalog):
    """Test that sample catalog is created successfully."""
    assert sample_catalog is not None
    assert isinstance(sample_catalog, SimpleCatalog)
    assert sample_catalog.name == "test_catalog"


def test_catalog_has_tables(sample_catalog):
    """Test that catalog contains expected tables."""
    assert len(sample_catalog.table) == 4
    
    table_names = [table.name for table in sample_catalog.table]
    assert "project1.dataset1.orders" in table_names
    assert "project1.dataset1.customers" in table_names
    assert "project1.dataset1.products" in table_names
    assert "project1.dataset1.order_items" in table_names


def test_orders_table_columns(sample_catalog):
    """Test orders table has correct columns."""
    orders = next(t for t in sample_catalog.table if "orders" in t.name)
    
    assert len(orders.column) == 4
    
    column_names = [col.name for col in orders.column]
    assert "order_id" in column_names
    assert "customer_id" in column_names
    assert "amount" in column_names
    assert "order_date" in column_names


def test_customers_table_columns(sample_catalog):
    """Test customers table has correct columns."""
    customers = next(t for t in sample_catalog.table if "customers" in t.name)
    
    assert len(customers.column) == 4
    
    column_names = [col.name for col in customers.column]
    assert "customer_id" in column_names
    assert "name" in column_names
    assert "email" in column_names
    assert "region" in column_names


def test_products_table_columns(sample_catalog):
    """Test products table has correct columns."""
    products = next(t for t in sample_catalog.table if "products" in t.name)
    
    assert len(products.column) == 4
    
    column_names = [col.name for col in products.column]
    assert "product_id" in column_names
    assert "name" in column_names
    assert "price" in column_names
    assert "category" in column_names


def test_order_items_table_columns(sample_catalog):
    """Test order_items table has correct columns."""
    order_items = next(t for t in sample_catalog.table if "order_items" in t.name)
    
    assert len(order_items.column) == 4
    
    column_names = [col.name for col in order_items.column]
    assert "order_id" in column_names
    assert "product_id" in column_names
    assert "quantity" in column_names
    assert "price" in column_names


def test_catalog_has_builtin_functions(sample_catalog):
    """Test that catalog includes builtin functions."""
    # Catalog should have builtin function options configured
    assert sample_catalog.builtin_function_options is not None
