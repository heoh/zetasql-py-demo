"""Tests for column-level lineage extraction.

Tests port examples from Java zetasql-toolkit and add Python-specific cases.
"""

import pytest

from zetasql_demo.lineage.column_lineage import (
    ColumnLineageExtractor,
    ExpressionParentFinder,
    ParentColumnFinder,
)
from zetasql_demo.lineage.models import ColumnEntity, ColumnLineage


class TestSimpleColumnLineage:
    """Basic column lineage tests."""
    
    def test_simple_column_reference(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for simple column selection."""
        query = "CREATE TABLE result AS SELECT title FROM product_catalog"
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "title")
        assert len(lineage.parents) == 1
        assert ColumnEntity("product_catalog", "title") in lineage.parents
    
    def test_column_with_alias(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for column with alias."""
        query = "CREATE TABLE result AS SELECT title AS product_title FROM product_catalog"
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "product_title")
        assert len(lineage.parents) == 1
        assert ColumnEntity("product_catalog", "title") in lineage.parents
    
    def test_function_applied_to_column(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for function applied to column."""
        query = "CREATE TABLE result AS SELECT UPPER(title) AS upper_title FROM product_catalog"
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "upper_title")
        assert len(lineage.parents) == 1
        assert ColumnEntity("product_catalog", "title") in lineage.parents
    
    def test_multiple_columns_combined(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for expression combining multiple columns."""
        query = """
        CREATE TABLE result AS 
        SELECT CONCAT(title, comment) AS combined 
        FROM product_catalog
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "combined")
        assert len(lineage.parents) == 2
        assert ColumnEntity("product_catalog", "title") in lineage.parents
        assert ColumnEntity("product_catalog", "comment") in lineage.parents
    
    def test_arithmetic_expression(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for arithmetic expression."""
        query = """
        CREATE TABLE result AS 
        SELECT price * quantity AS total_value
        FROM sales
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "total_value")
        assert len(lineage.parents) == 2
        assert ColumnEntity("sales", "price") in lineage.parents
        assert ColumnEntity("sales", "quantity") in lineage.parents
    
    def test_multiple_output_columns(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage with multiple output columns."""
        query = """
        CREATE TABLE result AS 
        SELECT 
            title,
            UPPER(comment) AS upper_comment,
            price
        FROM product_catalog
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 3
        
        # Convert to dict for easier checking
        lineage_map = {lineage.target.name: lineage for lineage in lineages}
        
        # Check title
        assert lineage_map["title"].target == ColumnEntity("result", "title")
        assert ColumnEntity("product_catalog", "title") in lineage_map["title"].parents
        
        # Check upper_comment
        assert lineage_map["upper_comment"].target == ColumnEntity("result", "upper_comment")
        assert ColumnEntity("product_catalog", "comment") in lineage_map["upper_comment"].parents
        
        # Check price
        assert lineage_map["price"].target == ColumnEntity("result", "price")
        assert ColumnEntity("product_catalog", "price") in lineage_map["price"].parents


class TestInsertLineage:
    """Tests for INSERT statement lineage."""
    
    def test_insert_from_select(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for INSERT with SELECT."""
        query = """
        INSERT INTO product_catalog (title, comment)
        SELECT title, comment FROM product_catalog_staging
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 2
        
        lineage_map = {lineage.target.name: lineage for lineage in lineages}
        
        assert ColumnEntity("product_catalog_staging", "title") in lineage_map["title"].parents
        assert ColumnEntity("product_catalog_staging", "comment") in lineage_map["comment"].parents


class TestJoinLineage:
    """Tests for JOIN queries."""
    
    def test_simple_join(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for simple JOIN."""
        query = """
        CREATE TABLE result AS
        SELECT 
            p.title,
            s.quantity
        FROM product_catalog p
        JOIN sales s ON p.product_id = s.product_id
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 2
        
        lineage_map = {lineage.target.name: lineage for lineage in lineages}
        
        assert ColumnEntity("product_catalog", "title") in lineage_map["title"].parents
        assert ColumnEntity("sales", "quantity") in lineage_map["quantity"].parents
    
    def test_join_with_computed_column(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for JOIN with computed column from multiple tables."""
        query = """
        CREATE TABLE result AS
        SELECT 
            CONCAT(p.title, s.product_id) AS combined
        FROM product_catalog p
        JOIN sales s ON p.product_id = s.product_id
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "combined")
        assert len(lineage.parents) == 2
        assert ColumnEntity("product_catalog", "title") in lineage.parents
        assert ColumnEntity("sales", "product_id") in lineage.parents


class TestSubqueryLineage:
    """Tests for subquery lineage."""
    
    def test_subquery_in_from(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage with subquery in FROM clause."""
        query = """
        CREATE TABLE result AS
        SELECT upper_title
        FROM (
            SELECT UPPER(title) AS upper_title
            FROM product_catalog
        )
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        # Should trace back to original column
        assert lineage.target == ColumnEntity("result", "upper_title")
        assert len(lineage.parents) == 1
        assert ColumnEntity("product_catalog", "title") in lineage.parents


class TestCTELineage:
    """Tests for CTE (WITH clause) lineage."""
    
    def test_simple_cte(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage with simple CTE."""
        query = """
        CREATE TABLE result AS
        WITH products AS (
            SELECT title, price FROM product_catalog
        )
        SELECT title FROM products
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "title")
        assert len(lineage.parents) == 1
        assert ColumnEntity("product_catalog", "title") in lineage.parents
    
    def test_cte_with_transformation(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage with CTE that transforms data."""
        query = """
        CREATE TABLE result AS
        WITH products AS (
            SELECT UPPER(title) AS upper_title FROM product_catalog
        )
        SELECT upper_title FROM products
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        # Should trace through CTE to original column
        assert lineage.target == ColumnEntity("result", "upper_title")
        assert len(lineage.parents) == 1
        assert ColumnEntity("product_catalog", "title") in lineage.parents


class TestAggregateFunctionLineage:
    """Tests for aggregate function lineage."""
    
    def test_sum_aggregate(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for SUM aggregate."""
        query = """
        CREATE TABLE result AS
        SELECT SUM(quantity) AS total_quantity
        FROM sales
        GROUP BY product_id
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "total_quantity")
        assert ColumnEntity("sales", "quantity") in lineage.parents
    
    def test_count_star(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for COUNT(*)."""
        query = """
        CREATE TABLE result AS
        SELECT product_id, COUNT(*) AS cnt
        FROM sales
        GROUP BY product_id
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        # Should have lineage for product_id and cnt
        assert len(lineages) >= 1
        
        lineage_map = {lineage.target.name: lineage for lineage in lineages}
        assert "product_id" in lineage_map


class TestCaseExpressionLineage:
    """Tests for CASE expression lineage."""
    
    def test_case_when(self, sample_catalog, analyzer, bigquery_language_options):
        """Test lineage for CASE WHEN expression."""
        query = """
        CREATE TABLE result AS
        SELECT 
            CASE 
                WHEN price > 100 THEN title
                ELSE comment
            END AS description
        FROM product_catalog
        """
        
        analyzed = analyzer.analyze_statement(query)
        lineages = ColumnLineageExtractor.extract(analyzed)
        
        assert len(lineages) == 1
        lineage = list(lineages)[0]
        
        assert lineage.target == ColumnEntity("result", "description")
        # CASE should include columns from THEN and ELSE, but not condition
        # So title and comment, but not price
        assert ColumnEntity("product_catalog", "title") in lineage.parents
        assert ColumnEntity("product_catalog", "comment") in lineage.parents
