"""Column-level lineage extraction demo.

Demonstrates extracting column-level lineage from various SQL statements.
Python port of ExtractColumnLevelLineage.java from zetasql-toolkit.
"""

import os
import sys

# Ensure the project `src` directory is on sys.path so `zetasql_demo` imports work
# This allows running the example directly (e.g. `python zetasql_demo/examples/demo_column_lineage.py`).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.abspath(os.path.join(_THIS_DIR, '..', '..'))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from zetasql.api import Analyzer
from zetasql.types import AnalyzerOptions

from zetasql_demo.catalog import create_sample_catalog
from zetasql_demo.lineage import ColumnLineageExtractor
from zetasql_demo.options import get_bigquery_language_options


def output_lineage(query: str, lineage_entries: set) -> None:
    """Print query and its column lineage.
    
    Args:
        query: SQL query string
        lineage_entries: Set of ColumnLineage objects
    """
    print("\nQuery:")
    print(query)
    print("\nLineage:")
    
    for lineage in sorted(lineage_entries, key=lambda x: (x.target.table, x.target.name)):
        print(f"{lineage.target.table}.{lineage.target.name}")
        for parent in sorted(lineage.parents, key=lambda x: (x.table, x.name)):
            print(f"\t\t<- {parent.table}.{parent.name}")
    
    print()
    print()


def demo_create_table_as_select(analyzer: Analyzer) -> None:
    """Demonstrate column lineage for CREATE TABLE AS SELECT.
    
    Shows how columns are traced through:
    - Nested subqueries
    - Function transformations (UPPER, CONCAT)
    - Column aliasing
    - GROUP BY
    
    Args:
        analyzer: Configured ZetaSQL Analyzer
    """
    query = """
        CREATE TABLE result_table AS
        SELECT
            concatted AS column_alias
        FROM
            (
                SELECT 
                    UPPER(CONCAT(title, comment)) AS concatted
                FROM product_catalog
            )
        GROUP BY 1
    """
    
    statement = analyzer.analyze_statement(query)
    lineage_entries = ColumnLineageExtractor.extract(statement)
    
    print("=" * 60)
    print("Extracted column lineage from CREATE TABLE AS SELECT")
    print("=" * 60)
    output_lineage(query, lineage_entries)


def demo_insert(analyzer: Analyzer) -> None:
    """Demonstrate column lineage for INSERT statement.
    
    Shows how INSERT maps query columns to target table columns:
    - Subquery with transformations
    - Function applications (LOWER, UPPER)
    - Column ordering in INSERT list
    
    Args:
        analyzer: Configured ZetaSQL Analyzer
    """
    query = """
        INSERT INTO product_catalog (title, comment)
        SELECT
            LOWER(upper_title) AS title_result,
            UPPER(lower_comment) AS comment_result
        FROM (
            SELECT
                UPPER(title) AS upper_title,
                LOWER(comment) AS lower_comment
            FROM product_catalog_staging
        )
    """
    
    statement = analyzer.analyze_statement(query)
    lineage_entries = ColumnLineageExtractor.extract(statement)
    
    print("=" * 60)
    print("Extracted column lineage from INSERT")
    print("=" * 60)
    output_lineage(query, lineage_entries)


def demo_update(analyzer: Analyzer) -> None:
    """Demonstrate column lineage for UPDATE statement.
    
    Shows how UPDATE SET clauses trace back to source columns:
    - UPDATE with FROM clause
    - Multiple SET assignments
    - Function transformations in SET expressions
    
    Args:
        analyzer: Configured ZetaSQL Analyzer
    """
    query = """
        UPDATE product_catalog AS W
        SET 
            title = S.product_id,
            comment = S.title
        FROM (
            SELECT product_id, UPPER(title) AS title 
            FROM product_catalog_staging
        ) AS S
        WHERE W.product_id = S.product_id
    """
    
    statement = analyzer.analyze_statement(query)
    lineage_entries = ColumnLineageExtractor.extract(statement)
    
    print("=" * 60)
    print("Extracted column lineage from UPDATE")
    print("=" * 60)
    output_lineage(query, lineage_entries)


def demo_merge(analyzer: Analyzer) -> None:
    """Demonstrate column lineage for MERGE statement.
    
    Shows how MERGE operations trace lineage:
    - MATCHED UPDATE case
    - NOT MATCHED INSERT case
    - Source query transformations
    
    Args:
        analyzer: Configured ZetaSQL Analyzer
    """
    query = """
        MERGE product_catalog AS W
        USING (
            SELECT product_id, UPPER(title) AS title 
            FROM product_catalog_staging
        ) AS S
        ON W.product_id = S.product_id
        WHEN MATCHED THEN
            UPDATE SET comment = S.title
        WHEN NOT MATCHED THEN
            INSERT(title) VALUES (UPPER(product_id))
    """
    
    statement = analyzer.analyze_statement(query)
    lineage_entries = ColumnLineageExtractor.extract(statement)
    
    print("=" * 60)
    print("Extracted column lineage from MERGE")
    print("=" * 60)
    output_lineage(query, lineage_entries)


def demo_complex_query(analyzer: Analyzer) -> None:
    """Demonstrate column lineage for complex query.
    
    Shows lineage through:
    - Common Table Expressions (WITH)
    - JOINs across multiple tables
    - Aggregate functions
    - CASE expressions
    - Multiple column transformations
    
    Args:
        analyzer: Configured ZetaSQL Analyzer
    """
    query = """
        CREATE TABLE sales_summary AS
        WITH product_prices AS (
            SELECT 
                product_id,
                AVG(price) AS avg_price
            FROM product_catalog
            GROUP BY product_id
        )
        SELECT
            s.product_id,
            SUM(s.quantity) AS total_quantity,
            SUM(s.price * s.quantity) AS total_revenue,
            CASE 
                WHEN p.avg_price > 100 THEN 'Premium'
                ELSE 'Standard'
            END AS price_category
        FROM sales s
        JOIN product_prices p ON s.product_id = p.product_id
        GROUP BY s.product_id, p.avg_price
    """
    
    statement = analyzer.analyze_statement(query)
    lineage_entries = ColumnLineageExtractor.extract(statement)
    
    print("=" * 60)
    print("Extracted column lineage from COMPLEX QUERY")
    print("=" * 60)
    output_lineage(query, lineage_entries)


def main():
    """Run all column lineage extraction demos."""
    print("\n" + "=" * 60)
    print("Column-Level Lineage Extraction Demo")
    print("Python port of zetasql-toolkit examples")
    print("=" * 60)
    
    # Setup catalog and analyzer
    language_options = get_bigquery_language_options()
    catalog = create_sample_catalog(language_options)
    
    options = AnalyzerOptions(language_options=language_options)
    analyzer = Analyzer(options, catalog)
    
    # Run demos
    try:
        demo_create_table_as_select(analyzer)
        print("-----------------------------------")
        
        demo_insert(analyzer)
        print("-----------------------------------")
        
        demo_update(analyzer)
        print("-----------------------------------")
        
        demo_merge(analyzer)
        print("-----------------------------------")
        
        demo_complex_query(analyzer)
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
