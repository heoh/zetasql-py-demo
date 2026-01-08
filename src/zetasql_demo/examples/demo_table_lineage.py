#!/usr/bin/env python3
"""Demo script for table-level lineage extraction.

Demonstrates lineage extraction for various SQL statement types:
- SELECT (single table, JOIN, subquery, CTE, UNION)
- CREATE TABLE AS SELECT
- CREATE VIEW
- INSERT
- UPDATE
- MERGE
"""

from zetasql.api import Analyzer
from zetasql.types import AnalyzerOptions

from zetasql_demo.catalog import create_sample_catalog
from zetasql_demo.options import get_bigquery_language_options
from zetasql_demo.lineage import extract_table_lineage, LineageFormatter


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_lineage(sql: str, lineage):
    """Print SQL and its lineage in both formats."""
    print("\nSQL:")
    print("-" * 80)
    print(sql.strip())
    print()
    
    print("Lineage (Text):")
    print("-" * 80)
    print(LineageFormatter.to_text(lineage))
    print()
    
    print("Lineage (JSON):")
    print("-" * 80)
    print(LineageFormatter.to_json(lineage))
    print()


def demo_select_statements(analyzer: Analyzer):
    """Demonstrate SELECT statement lineage."""
    print_section("SELECT Statements")
    
    # Single table
    sql = """
    SELECT order_id, customer_id, amount
    FROM `project1.dataset1.orders`
    WHERE amount > 100
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)
    
    # JOIN
    sql = """
    SELECT o.order_id, c.name, o.amount
    FROM `project1.dataset1.orders` o
    JOIN `project1.dataset1.customers` c
    ON o.customer_id = c.customer_id
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)
    
    # CTE
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
    print_lineage(sql, lineage)


def demo_create_statements(analyzer: Analyzer):
    """Demonstrate CREATE statement lineage."""
    print_section("CREATE Statements")
    
    # CREATE TABLE AS SELECT
    sql = """
    CREATE TABLE `project1.dataset1.order_summary` AS
    SELECT customer_id, COUNT(*) as order_count, SUM(amount) as total_amount
    FROM `project1.dataset1.orders`
    GROUP BY customer_id
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)
    
    # CREATE VIEW
    sql = """
    CREATE VIEW `project1.dataset1.customer_orders` AS
    SELECT 
        c.customer_id,
        c.name,
        c.email,
        o.order_id,
        o.amount,
        o.order_date
    FROM `project1.dataset1.customers` c
    LEFT JOIN `project1.dataset1.orders` o
    ON c.customer_id = o.customer_id
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)


def demo_dml_statements(analyzer: Analyzer):
    """Demonstrate DML statement lineage."""
    print_section("DML Statements")
    
    # INSERT
    sql = """
    INSERT INTO `project1.dataset1.orders` (order_id, customer_id, amount, order_date)
    SELECT 
        order_id,
        order_id as customer_id,
        price * quantity as amount,
        CURRENT_DATE()
    FROM `project1.dataset1.order_items`
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)
    
    # UPDATE
    sql = """
    UPDATE `project1.dataset1.orders` o
    SET amount = amount * 1.1
    WHERE customer_id IN (
        SELECT customer_id 
        FROM `project1.dataset1.customers`
        WHERE region = 'US'
    )
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)
    
    # MERGE
    sql = """
    MERGE `project1.dataset1.orders` target
    USING `project1.dataset1.order_items` source
    ON target.order_id = source.order_id
    WHEN MATCHED THEN
        UPDATE SET amount = source.price * source.quantity
    WHEN NOT MATCHED THEN
        INSERT (order_id, customer_id, amount) 
        VALUES (source.order_id, source.product_id, source.price)
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)


def demo_complex_queries(analyzer: Analyzer):
    """Demonstrate complex query lineage."""
    print_section("Complex Queries")
    
    # Multiple CTEs with joins
    sql = """
    WITH 
    order_totals AS (
        SELECT customer_id, SUM(amount) as total
        FROM `project1.dataset1.orders`
        GROUP BY customer_id
    ),
    product_purchases AS (
        SELECT customer_id, COUNT(DISTINCT product_id) as unique_products
        FROM `project1.dataset1.orders` o
        JOIN `project1.dataset1.order_items` oi ON o.order_id = oi.order_id
        GROUP BY customer_id
    )
    SELECT 
        c.customer_id,
        c.name,
        c.region,
        ot.total,
        pp.unique_products
    FROM `project1.dataset1.customers` c
    LEFT JOIN order_totals ot ON c.customer_id = ot.customer_id
    LEFT JOIN product_purchases pp ON c.customer_id = pp.customer_id
    """
    stmt = analyzer.analyze_statement(sql)
    lineage = extract_table_lineage(stmt)
    print_lineage(sql, lineage)


def main():
    """Run all table lineage demos."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "Table-Level Lineage Extraction Demo" + " " * 23 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Setup
    lang_opts = get_bigquery_language_options()
    catalog = create_sample_catalog(lang_opts)
    options = AnalyzerOptions(language_options=lang_opts)
    analyzer = Analyzer(options, catalog)
    
    # Run demos
    demo_select_statements(analyzer)
    demo_create_statements(analyzer)
    demo_dml_statements(analyzer)
    demo_complex_queries(analyzer)
    
    print("\n" + "=" * 80)
    print("  Demo Complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
