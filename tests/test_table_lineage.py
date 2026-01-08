"""Tests for table-level lineage extraction."""

import pytest
from zetasql.api import Analyzer

from zetasql_demo.lineage import extract_table_lineage, TableLineage


class TestSelectStatements:
    """Tests for SELECT statement lineage."""
    
    def test_select_single_table(self, analyzer: Analyzer):
        """Test SELECT from single table."""
        sql = "SELECT * FROM `project1.dataset1.orders`"
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert lineage.target is None  # SELECT has no target
        assert "project1.dataset1.orders" in lineage.sources
        assert len(lineage.sources) == 1
    
    def test_select_join(self, analyzer: Analyzer):
        """Test SELECT with JOIN."""
        sql = """
        SELECT o.order_id, c.name
        FROM `project1.dataset1.orders` o
        JOIN `project1.dataset1.customers` c
        ON o.customer_id = c.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert lineage.target is None
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources
        assert len(lineage.sources) == 2
    
    def test_select_subquery(self, analyzer: Analyzer):
        """Test SELECT with subquery."""
        sql = """
        SELECT * FROM (
            SELECT order_id, amount
            FROM `project1.dataset1.orders`
            WHERE amount > 100
        ) AS subquery
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
        assert len(lineage.sources) == 1
    
    def test_select_cte(self, analyzer: Analyzer):
        """Test SELECT with CTE (WITH clause)."""
        sql = """
        WITH order_summary AS (
            SELECT customer_id, SUM(amount) as total
            FROM `project1.dataset1.orders`
            GROUP BY customer_id
        )
        SELECT c.name, os.total
        FROM order_summary os
        JOIN `project1.dataset1.customers` c
        ON os.customer_id = c.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources
        assert len(lineage.sources) == 2
    
    def test_select_union(self, analyzer: Analyzer):
        """Test SELECT with UNION."""
        sql = """
        SELECT order_id FROM `project1.dataset1.orders`
        UNION ALL
        SELECT order_id FROM `project1.dataset1.order_items`
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources
        assert len(lineage.sources) == 2


class TestCreateStatements:
    """Tests for CREATE statement lineage."""
    
    def test_create_table_as_select(self, analyzer: Analyzer):
        """Test CREATE TABLE AS SELECT."""
        sql = """
        CREATE TABLE `project1.dataset1.order_summary` AS
        SELECT customer_id, SUM(amount) as total_amount
        FROM `project1.dataset1.orders`
        GROUP BY customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "CREATE_TABLE_AS_SELECT"
        assert lineage.target == "project1.dataset1.order_summary"
        assert "project1.dataset1.orders" in lineage.sources
        assert len(lineage.sources) == 1
    
    def test_create_view(self, analyzer: Analyzer):
        """Test CREATE VIEW."""
        sql = """
        CREATE VIEW `project1.dataset1.customer_orders` AS
        SELECT c.customer_id, c.name, o.order_id, o.amount
        FROM `project1.dataset1.customers` c
        JOIN `project1.dataset1.orders` o
        ON c.customer_id = o.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "CREATE_VIEW"
        assert lineage.target == "project1.dataset1.customer_orders"
        assert "project1.dataset1.customers" in lineage.sources
        assert "project1.dataset1.orders" in lineage.sources
        assert len(lineage.sources) == 2


class TestDMLStatements:
    """Tests for DML statement lineage."""
    
    def test_insert(self, analyzer: Analyzer):
        """Test INSERT statement."""
        sql = """
        INSERT INTO `project1.dataset1.orders` (order_id, customer_id, amount, order_date)
        SELECT order_id, order_id as customer_id, price, CURRENT_DATE()
        FROM `project1.dataset1.order_items`
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "INSERT"
        assert lineage.target == "project1.dataset1.orders"
        assert "project1.dataset1.order_items" in lineage.sources
        # Note: target table may also appear in sources depending on analysis
        assert len(lineage.sources) >= 1
    
    def test_update(self, analyzer: Analyzer):
        """Test UPDATE statement."""
        sql = """
        UPDATE `project1.dataset1.orders` o
        SET amount = amount * 1.1
        WHERE customer_id IN (
            SELECT customer_id FROM `project1.dataset1.customers`
            WHERE region = 'US'
        )
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "UPDATE"
        assert lineage.target == "project1.dataset1.orders"
        assert "project1.dataset1.orders" in lineage.sources  # Self-reference
        assert "project1.dataset1.customers" in lineage.sources
        assert len(lineage.sources) == 2
    
    def test_update_with_from(self, analyzer: Analyzer):
        """Test UPDATE with FROM clause."""
        sql = """
        UPDATE `project1.dataset1.orders` o
        SET amount = oi.price
        FROM `project1.dataset1.order_items` oi
        WHERE o.order_id = oi.order_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "UPDATE"
        assert lineage.target == "project1.dataset1.orders"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources
        assert len(lineage.sources) == 2
    
    def test_merge(self, analyzer: Analyzer):
        """Test MERGE statement."""
        sql = """
        MERGE `project1.dataset1.orders` target
        USING `project1.dataset1.order_items` source
        ON target.order_id = source.order_id
        WHEN MATCHED THEN
            UPDATE SET amount = source.price * source.quantity
        WHEN NOT MATCHED THEN
            INSERT (order_id, amount) VALUES (source.order_id, source.price)
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "MERGE"
        assert lineage.target == "project1.dataset1.orders"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources
        assert len(lineage.sources) == 2


class TestComplexQueries:
    """Tests for complex query lineage."""
    
    def test_nested_subqueries(self, analyzer: Analyzer):
        """Test deeply nested subqueries."""
        sql = """
        SELECT * FROM (
            SELECT * FROM (
                SELECT customer_id, SUM(amount) as total
                FROM `project1.dataset1.orders`
                GROUP BY customer_id
            ) AS inner_query
            WHERE total > 1000
        ) AS outer_query
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
        assert len(lineage.sources) == 1
    
    def test_multiple_ctes(self, analyzer: Analyzer):
        """Test multiple CTEs."""
        sql = """
        WITH order_totals AS (
            SELECT customer_id, SUM(amount) as total
            FROM `project1.dataset1.orders`
            GROUP BY customer_id
        ),
        customer_info AS (
            SELECT customer_id, name, region
            FROM `project1.dataset1.customers`
        )
        SELECT ci.name, ci.region, ot.total
        FROM customer_info ci
        JOIN order_totals ot ON ci.customer_id = ot.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources
        assert len(lineage.sources) == 2
    
    def test_create_table_with_complex_query(self, analyzer: Analyzer):
        """Test CREATE TABLE AS with complex query."""
        sql = """
        CREATE TABLE `project1.dataset1.customer_analysis` AS
        WITH order_stats AS (
            SELECT 
                o.customer_id,
                COUNT(*) as order_count,
                SUM(o.amount) as total_amount
            FROM `project1.dataset1.orders` o
            JOIN `project1.dataset1.order_items` oi
            ON o.order_id = oi.order_id
            GROUP BY o.customer_id
        )
        SELECT 
            c.customer_id,
            c.name,
            c.region,
            os.order_count,
            os.total_amount
        FROM `project1.dataset1.customers` c
        LEFT JOIN order_stats os ON c.customer_id = os.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "CREATE_TABLE_AS_SELECT"
        assert lineage.target == "project1.dataset1.customer_analysis"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources
        assert len(lineage.sources) == 3
