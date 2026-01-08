"""Tests for table-level lineage extraction.

Tests cover all SQL statement types supported by zetasql-toolkit:
- SELECT (various forms)
- CREATE TABLE AS SELECT
- CREATE VIEW
- INSERT
- UPDATE
- MERGE
- Complex queries (subqueries, CTEs, JOINs, UNION)
"""

import pytest
from zetasql_demo.lineage import extract_table_lineage, TableLineage


class TestSelectStatements:
    """Tests for SELECT statement lineage extraction."""
    
    def test_select_single_table(self, analyzer):
        """SELECT from a single table."""
        sql = "SELECT * FROM `project1.dataset1.orders`"
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert lineage.target is None  # SELECT has no target table
        assert "project1.dataset1.orders" in lineage.sources
        assert len(lineage.sources) == 1
    
    def test_select_with_join(self, analyzer):
        """SELECT with JOIN from multiple tables."""
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
    
    def test_select_with_subquery(self, analyzer):
        """SELECT with subquery."""
        sql = """
            SELECT order_id, amount
            FROM (
                SELECT order_id, amount, customer_id
                FROM `project1.dataset1.orders`
                WHERE amount > 100
            )
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
    
    def test_select_with_cte(self, analyzer):
        """SELECT with CTE (WITH clause)."""
        sql = """
            WITH high_value_orders AS (
                SELECT order_id, customer_id, amount
                FROM `project1.dataset1.orders`
                WHERE amount > 1000
            )
            SELECT h.order_id, c.name
            FROM high_value_orders h
            JOIN `project1.dataset1.customers` c
                ON h.customer_id = c.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources
    
    def test_select_with_union(self, analyzer):
        """SELECT with UNION."""
        sql = """
            SELECT order_id, amount FROM `project1.dataset1.orders`
            UNION ALL
            SELECT order_id, price FROM `project1.dataset1.order_items`
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "SELECT"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources


class TestCreateTableAsSelect:
    """Tests for CREATE TABLE AS SELECT lineage extraction."""
    
    def test_create_table_as_select_simple(self, analyzer):
        """CREATE TABLE AS SELECT from single table."""
        sql = """
            CREATE TABLE `project1.dataset1.high_value_orders` AS
            SELECT order_id, customer_id, amount
            FROM `project1.dataset1.orders`
            WHERE amount > 1000
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "CREATE_TABLE_AS_SELECT"
        assert lineage.target == "project1.dataset1.high_value_orders"
        assert "project1.dataset1.orders" in lineage.sources
    
    def test_create_table_as_select_with_join(self, analyzer):
        """CREATE TABLE AS SELECT with JOIN."""
        sql = """
            CREATE TABLE `project1.dataset1.order_summary` AS
            SELECT 
                o.order_id,
                c.name AS customer_name,
                o.amount
            FROM `project1.dataset1.orders` o
            JOIN `project1.dataset1.customers` c
                ON o.customer_id = c.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "CREATE_TABLE_AS_SELECT"
        assert lineage.target == "project1.dataset1.order_summary"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources


class TestCreateView:
    """Tests for CREATE VIEW lineage extraction."""
    
    def test_create_view_simple(self, analyzer):
        """CREATE VIEW from single table."""
        sql = """
            CREATE VIEW `project1.dataset1.customer_orders` AS
            SELECT 
                c.customer_id,
                c.name,
                COUNT(o.order_id) AS order_count
            FROM `project1.dataset1.customers` c
            LEFT JOIN `project1.dataset1.orders` o
                ON c.customer_id = o.customer_id
            GROUP BY c.customer_id, c.name
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "CREATE_VIEW"
        assert lineage.target == "project1.dataset1.customer_orders"
        assert "project1.dataset1.customers" in lineage.sources
        assert "project1.dataset1.orders" in lineage.sources


class TestInsertStatement:
    """Tests for INSERT statement lineage extraction."""
    
    def test_insert_from_select(self, analyzer):
        """INSERT INTO from SELECT."""
        sql = """
            INSERT INTO `project1.dataset1.orders` (order_id, customer_id, amount, order_date)
            SELECT 
                order_id,
                product_id AS customer_id,
                price AS amount,
                CURRENT_DATE() AS order_date
            FROM `project1.dataset1.order_items`
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "INSERT"
        assert lineage.target == "project1.dataset1.orders"
        assert "project1.dataset1.order_items" in lineage.sources


class TestUpdateStatement:
    """Tests for UPDATE statement lineage extraction."""
    
    def test_update_simple(self, analyzer):
        """UPDATE with simple SET."""
        sql = """
            UPDATE `project1.dataset1.orders`
            SET amount = amount * 1.1
            WHERE order_id = 123
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "UPDATE"
        assert lineage.target == "project1.dataset1.orders"
        # UPDATE reads from itself
        assert "project1.dataset1.orders" in lineage.sources
    
    def test_update_with_join(self, analyzer):
        """UPDATE with JOIN (FROM clause)."""
        sql = """
            UPDATE `project1.dataset1.orders` o
            SET o.amount = o.amount * 1.1
            FROM `project1.dataset1.customers` c
            WHERE o.customer_id = c.customer_id AND c.region = 'US'
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "UPDATE"
        assert lineage.target == "project1.dataset1.orders"
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources


class TestMergeStatement:
    """Tests for MERGE statement lineage extraction."""
    
    def test_merge_simple(self, analyzer):
        """MERGE statement with MATCHED and NOT MATCHED."""
        sql = """
            MERGE `project1.dataset1.orders` target
            USING `project1.dataset1.order_items` source
            ON target.order_id = source.order_id
            WHEN MATCHED THEN
                UPDATE SET amount = source.price
            WHEN NOT MATCHED THEN
                INSERT (order_id, amount) VALUES (source.order_id, source.price)
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert lineage.statement_type == "MERGE"
        assert lineage.target == "project1.dataset1.orders"
        # MERGE reads from both target and source
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources


class TestComplexQueries:
    """Tests for complex queries with nested structures."""
    
    def test_nested_subqueries(self, analyzer):
        """Deeply nested subqueries."""
        sql = """
            SELECT order_id, total_amount
            FROM (
                SELECT order_id, SUM(amount) AS total_amount
                FROM (
                    SELECT o.order_id, oi.price AS amount
                    FROM `project1.dataset1.orders` o
                    JOIN `project1.dataset1.order_items` oi
                        ON o.order_id = oi.order_id
                )
                GROUP BY order_id
            )
            WHERE total_amount > 500
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources
    
    def test_cte_with_multiple_references(self, analyzer):
        """CTE that references multiple tables."""
        sql = """
            WITH 
            order_totals AS (
                SELECT order_id, SUM(quantity * price) AS total
                FROM `project1.dataset1.order_items`
                GROUP BY order_id
            ),
            customer_orders AS (
                SELECT o.customer_id, ot.total
                FROM `project1.dataset1.orders` o
                JOIN order_totals ot ON o.order_id = ot.order_id
            )
            SELECT c.name, co.total
            FROM `project1.dataset1.customers` c
            JOIN customer_orders co ON c.customer_id = co.customer_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert "project1.dataset1.order_items" in lineage.sources
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources
    
    def test_union_of_complex_queries(self, analyzer):
        """UNION of queries with JOINs."""
        sql = """
            SELECT o.order_id, c.name, 'direct' AS source
            FROM `project1.dataset1.orders` o
            JOIN `project1.dataset1.customers` c ON o.customer_id = c.customer_id
            
            UNION ALL
            
            SELECT oi.order_id, p.name, 'item' AS source
            FROM `project1.dataset1.order_items` oi
            JOIN `project1.dataset1.products` p ON oi.product_id = p.product_id
        """
        stmt = analyzer.analyze_statement(sql)
        
        lineage = extract_table_lineage(stmt)
        
        assert "project1.dataset1.orders" in lineage.sources
        assert "project1.dataset1.customers" in lineage.sources
        assert "project1.dataset1.order_items" in lineage.sources
        assert "project1.dataset1.products" in lineage.sources
