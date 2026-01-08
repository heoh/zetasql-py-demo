"""Tests for column-level lineage extraction."""

import pytest
from zetasql.api import Analyzer, ResolvedStatement
from zetasql.types import SimpleCatalog, LanguageOptions

from zetasql_demo.lineage.column_lineage import ColumnLineageExtractor
from zetasql_demo.lineage.models import ColumnEntity, ColumnLineage


class TestSelectStatements:
    """Test column lineage extraction for SELECT statements."""
    
    def test_select_all_columns(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT * extracts all columns."""
        sql = """
        SELECT *
        FROM `project1.dataset1.customers`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have lineages for customer_id, name, email
        assert len(lineages) == 3
        
        # Check customer_id lineage
        customer_id_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'customer_id'),
            None
        )
        assert customer_id_lineage is not None
        assert len(customer_id_lineage.sources) == 1
        source = list(customer_id_lineage.sources)[0]
        assert source.table_name == 'project1.dataset1.customers'
        assert source.name.lower() == 'customer_id'
    
    def test_select_specific_columns(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT with specific columns."""
        sql = """
        SELECT customer_id, name
        FROM `project1.dataset1.customers`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have exactly 2 lineages
        assert len(lineages) == 2
        
        # All lineages should have 1 source each
        for lineage in lineages:
            assert len(lineage.sources) == 1
            source = list(lineage.sources)[0]
            assert source.table_name == 'project1.dataset1.customers'
    
    def test_select_with_alias(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT with column aliases."""
        sql = """
        SELECT 
            customer_id AS id,
            name AS customer_name
        FROM `project1.dataset1.customers`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 2 lineages with aliased names
        assert len(lineages) == 2
        
        # Check id column lineage
        id_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'id'),
            None
        )
        assert id_lineage is not None
        assert len(id_lineage.sources) == 1
        source = list(id_lineage.sources)[0]
        assert source.name.lower() == 'customer_id'
    
    def test_select_with_expression(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT with expressions."""
        sql = """
        SELECT 
            customer_id,
            UPPER(name) AS upper_name,
            quantity * price AS total
        FROM `project1.dataset1.orders`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 3 lineages
        assert len(lineages) == 3
        
        # Check upper_name lineage (derived from name)
        upper_name_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'upper_name'),
            None
        )
        assert upper_name_lineage is not None
        assert len(upper_name_lineage.sources) == 1
        source = list(upper_name_lineage.sources)[0]
        assert source.name.lower() == 'name'
        
        # Check total lineage (derived from quantity and price)
        total_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'total'),
            None
        )
        assert total_lineage is not None
        assert len(total_lineage.sources) == 2
        source_names = {s.name.lower() for s in total_lineage.sources}
        assert source_names == {'quantity', 'price'}
    
    def test_select_with_join(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT with JOIN."""
        sql = """
        SELECT 
            c.customer_id,
            c.name,
            o.order_id,
            o.quantity
        FROM `project1.dataset1.customers` c
        JOIN `project1.dataset1.orders` o
        ON c.customer_id = o.customer_id
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 4 lineages
        assert len(lineages) == 4
        
        # Check customer_id from customers
        customer_id_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'customer_id'),
            None
        )
        assert customer_id_lineage is not None
        assert len(customer_id_lineage.sources) == 1
        source = list(customer_id_lineage.sources)[0]
        assert source.table_name == 'project1.dataset1.customers'
        
        # Check order_id from orders
        order_id_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'order_id'),
            None
        )
        assert order_id_lineage is not None
        assert len(order_id_lineage.sources) == 1
        source = list(order_id_lineage.sources)[0]
        assert source.table_name == 'project1.dataset1.orders'


class TestCreateTableAsSelect:
    """Test column lineage extraction for CREATE TABLE AS SELECT."""
    
    def test_create_table_simple(self, sample_catalog: SimpleCatalog, analyzer):
        """Test CREATE TABLE AS SELECT with simple columns."""
        sql = """
        CREATE TABLE `project1.dataset1.customer_summary` AS
        SELECT 
            customer_id,
            name,
            email
        FROM `project1.dataset1.customers`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 3 lineages
        assert len(lineages) == 3
        
        # All targets should have project1.dataset1.customer_summary
        for lineage in lineages:
            assert lineage.target.table_name == 'project1.dataset1.customer_summary'
            assert len(lineage.sources) == 1
            source = list(lineage.sources)[0]
            assert source.table_name == 'project1.dataset1.customers'
    
    def test_create_table_with_aggregation(self, sample_catalog: SimpleCatalog, analyzer):
        """Test CREATE TABLE AS SELECT with aggregation."""
        sql = """
        CREATE TABLE `project1.dataset1.customer_totals` AS
        SELECT 
            customer_id,
            SUM(quantity) AS total_quantity,
            SUM(price) AS total_price
        FROM `project1.dataset1.orders`
        GROUP BY customer_id
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 3 lineages
        assert len(lineages) == 3
        
        # Check total_quantity lineage
        total_qty_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'total_quantity'),
            None
        )
        assert total_qty_lineage is not None
        assert len(total_qty_lineage.sources) == 1
        source = list(total_qty_lineage.sources)[0]
        assert source.name.lower() == 'quantity'


class TestCreateView:
    """Test column lineage extraction for CREATE VIEW."""
    
    def test_create_view_simple(self, sample_catalog: SimpleCatalog, analyzer):
        """Test CREATE VIEW with simple columns."""
        sql = """
        CREATE VIEW `project1.dataset1.active_customers` AS
        SELECT 
            customer_id,
            name,
            email
        FROM `project1.dataset1.customers`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 3 lineages
        assert len(lineages) == 3
        
        # All targets should reference the view
        for lineage in lineages:
            assert lineage.target.table_name == 'project1.dataset1.active_customers'


class TestInsertStatement:
    """Test column lineage extraction for INSERT statements."""
    
    def test_insert_with_column_list(self, sample_catalog: SimpleCatalog, analyzer):
        """Test INSERT with explicit column list."""
        sql = """
        INSERT INTO `project1.dataset1.orders` (customer_id, quantity, price, name)
        SELECT 
            customer_id,
            10 AS quantity,
            100.0 AS price,
            name
        FROM `project1.dataset1.customers`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 4 lineages (order_id is auto-generated, not in INSERT)
        assert len(lineages) == 4
        
        # Check customer_id mapping
        customer_id_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'customer_id'),
            None
        )
        assert customer_id_lineage is not None
        assert lineage.target.table_name == 'project1.dataset1.orders'
        assert len(customer_id_lineage.sources) == 1


class TestComplexQueries:
    """Test column lineage extraction for complex queries."""
    
    def test_subquery(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT with subquery."""
        sql = """
        SELECT 
            c.customer_id,
            c.name,
            summary.total_orders
        FROM `project1.dataset1.customers` c
        JOIN (
            SELECT customer_id, SUM(quantity) AS total_orders
            FROM `project1.dataset1.orders`
            GROUP BY customer_id
        ) summary
        ON c.customer_id = summary.customer_id
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 3 lineages
        assert len(lineages) == 3
        
        # Check total_orders lineage (comes from aggregated quantity)
        total_orders_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'total_orders'),
            None
        )
        assert total_orders_lineage is not None
        assert len(total_orders_lineage.sources) == 1
        source = list(total_orders_lineage.sources)[0]
        assert source.table_name == 'project1.dataset1.orders'
        assert source.name.lower() == 'quantity'
    
    def test_cte(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT with CTE."""
        sql = """
        WITH customer_orders AS (
            SELECT 
                customer_id,
                SUM(quantity) AS total_quantity
            FROM `project1.dataset1.orders`
            GROUP BY customer_id
        )
        SELECT 
            c.customer_id,
            c.name,
            co.total_quantity
        FROM `project1.dataset1.customers` c
        JOIN customer_orders co
        ON c.customer_id = co.customer_id
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 3 lineages
        assert len(lineages) == 3
        
        # Check total_quantity lineage (from CTE aggregation)
        total_qty_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'total_quantity'),
            None
        )
        assert total_qty_lineage is not None
        # Should trace back to orders.quantity through the CTE
        assert any(
            s.table_name == 'project1.dataset1.orders' and s.name.lower() == 'quantity'
            for s in total_qty_lineage.sources
        )
    
    def test_union(self, sample_catalog: SimpleCatalog, analyzer):
        """Test SELECT with UNION."""
        sql = """
        SELECT customer_id, name AS identifier
        FROM `project1.dataset1.customers`
        UNION ALL
        SELECT order_id AS customer_id, name AS identifier
        FROM `project1.dataset1.orders`
        """
        
        statement = analyzer(sql, sample_catalog)
        extractor = ColumnLineageExtractor(statement)
        lineages = extractor.extract()
        
        # Should have 2 lineages (customer_id and identifier)
        assert len(lineages) == 2
        
        # Check customer_id lineage (comes from both customers.customer_id and orders.order_id)
        customer_id_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'customer_id'),
            None
        )
        assert customer_id_lineage is not None
        assert len(customer_id_lineage.sources) == 2
        
        # Check identifier lineage (comes from both customers.name and orders.name)
        identifier_lineage = next(
            (l for l in lineages if l.target.name.lower() == 'identifier'),
            None
        )
        assert identifier_lineage is not None
        assert len(identifier_lineage.sources) == 2
        source_tables = {s.table_name for s in identifier_lineage.sources}
        assert 'project1.dataset1.customers' in source_tables
        assert 'project1.dataset1.orders' in source_tables
