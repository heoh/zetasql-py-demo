# ZetaSQL Lineage Demo - Python

Python implementation of column and table-level lineage extraction using ZetaSQL, ported from [GoogleCloudPlatform/zetasql-toolkit](https://github.com/GoogleCloudPlatform/zetasql-toolkit).

## Overview

This project demonstrates how to extract data lineage (both table-level and column-level) from SQL queries using ZetaSQL's Python API. It provides a Python port of the lineage extraction functionality from the Java-based zetasql-toolkit.

### Features

- **Table-level lineage**: Track which source tables contribute to target tables
- **Column-level lineage**: Trace individual columns back to their terminal source columns
- **BigQuery SQL dialect**: Full support for BigQuery SQL syntax
- **Complex query support**: Handles JOINs, CTEs, subqueries, aggregations, window functions, and more
- **Multiple statement types**: SELECT, CREATE TABLE AS SELECT, CREATE VIEW, INSERT, UPDATE, MERGE

## Installation

### Prerequisites

- Python 3.8+
- ZetaSQL Python library

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd zetasql-py-demo
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run tests to verify installation:
```bash
pytest
```

## Quick Start

### Table-Level Lineage

```python
from zetasql.api import Analyzer
from zetasql.types import AnalyzerOptions

from zetasql_demo.catalog import create_sample_catalog
from zetasql_demo.lineage import extract_table_lineage
from zetasql_demo.options import get_bigquery_language_options

# Setup
language_options = get_bigquery_language_options()
catalog = create_sample_catalog(language_options)
options = AnalyzerOptions(language_options=language_options)
analyzer = Analyzer(options, catalog)

# Analyze SQL
sql = """
    SELECT o.order_id, c.name, o.amount
    FROM project1.dataset1.orders o
    JOIN project1.dataset1.customers c
    ON o.customer_id = c.customer_id
"""
statement = analyzer.analyze_statement(sql)

# Extract lineage
lineage = extract_table_lineage(statement)

print(f"Target: {lineage.target}")
print(f"Sources: {lineage.sources}")
print(f"Statement Type: {lineage.statement_type}")
```

### Column-Level Lineage

```python
from zetasql_demo.lineage import ColumnLineageExtractor

sql = """
    CREATE TABLE result_table AS
    SELECT 
        UPPER(CONCAT(title, comment)) AS combined_text
    FROM product_catalog
"""
statement = analyzer.analyze_statement(sql)

# Extract column lineage
lineages = ColumnLineageExtractor.extract(statement)

for lineage in lineages:
    print(f"{lineage.target.table}.{lineage.target.name}")
    for parent in lineage.parents:
        print(f"    <- {parent.table}.{parent.name}")
```

Output:
```
result_table.combined_text
    <- product_catalog.comment
    <- product_catalog.title
```

## Running Examples

### Table Lineage Demo

```bash
cd /home/heoh/workspaces/zetasql-py-demo
PYTHONPATH=src python src/zetasql_demo/examples/demo_table_lineage.py
```

Demonstrates lineage extraction for:
- SELECT statements (single table, JOINs, subqueries, CTEs)
- CREATE TABLE AS SELECT
- INSERT, UPDATE, MERGE

### Column Lineage Demo

```bash
PYTHONPATH=src python src/zetasql_demo/examples/demo_column_lineage.py
```

Shows column-level lineage for:
- CREATE TABLE AS SELECT with nested transformations
- INSERT with subqueries
- UPDATE with FROM clause
- MERGE with MATCHED/NOT MATCHED cases
- Complex queries with CTEs, JOINs, and aggregations

## Project Structure

```
zetasql-py-demo/
├── src/
│   └── zetasql_demo/
│       ├── catalog/              # Sample catalog creation
│       │   ├── __init__.py
│       │   └── sample_catalog.py
│       ├── options/              # BigQuery language options
│       │   ├── __init__.py
│       │   └── bigquery_options.py
│       ├── lineage/              # Core lineage extraction
│       │   ├── __init__.py
│       │   ├── models.py         # Data models (ColumnEntity, etc.)
│       │   ├── table_lineage.py  # Table-level extraction
│       │   ├── column_lineage.py # Column-level extraction
│       │   └── formatters.py     # Output formatting
│       └── examples/             # Runnable demos
│           ├── demo_table_lineage.py
│           └── demo_column_lineage.py
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_catalog.py
│   ├── test_table_lineage.py
│   └── test_column_lineage.py
├── docs/
│   ├── PROJECT_OVERVIEW.md
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   └── TODO.md
├── pytest.ini
├── requirements.txt
└── README.md
```

## Architecture

### Data Models

- **ColumnEntity**: Represents a column in a table (table name + column name)
- **ColumnLineage**: Maps a target column to its parent columns
- **TableLineage**: Maps a target table to its source tables

### Core Components

1. **ExpressionParentFinder**: Finds direct parent columns of an expression
   - Handles function calls, subqueries, STRUCT field access
   - Special logic for CASE, IF, NULLIF (only value branches, not conditions)

2. **ParentColumnFinder**: Finds terminal parent columns using BFS
   - Traverses computed columns back to table scans
   - Handles CTEs (WITH clauses) with scope management
   - Supports UNION, UNNEST, and other set operations
   - Recursively expands STRUCT fields

3. **ColumnLineageExtractor**: Main entry point for column lineage
   - Dispatches to appropriate handler based on statement type
   - Supports CREATE TABLE AS SELECT, INSERT, UPDATE, MERGE

4. **TableLineageExtractor**: Extracts table-level lineage
   - Uses ResolvedNodeVisitor pattern to traverse AST
   - Collects source tables from TableScan nodes
   - Identifies target tables from statement types

## Testing

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_column_lineage.py -v
```

Run with coverage:
```bash
pytest --cov=src/zetasql_demo --cov-report=html
```

### Test Coverage

- **Table lineage**: 14 test cases covering all SQL statement types
- **Column lineage**: 15 test cases covering simple to complex scenarios
- **Catalog & Options**: Basic validation tests

## API Reference

### ColumnLineageExtractor

```python
@staticmethod
def extract(statement: ResolvedStatement) -> Set[ColumnLineage]:
    """Extract column lineage from a resolved SQL statement.
    
    Args:
        statement: Analyzed ResolvedStatement from ZetaSQL
        
    Returns:
        Set of ColumnLineage objects showing column dependencies
    """
```

### ParentColumnFinder

```python
@staticmethod
def find_parents_for_column(
    statement: ResolvedStatement, 
    column: ResolvedColumn
) -> List[ResolvedColumn]:
    """Find terminal parent columns for a column.
    
    Uses BFS to trace back through computed columns to table scans.
    
    Args:
        statement: Statement containing the column
        column: Column to find parents for
        
    Returns:
        List of terminal parent ResolvedColumns
    """
```

### ExpressionParentFinder

```python
@staticmethod
def find_direct_parents(expression: ResolvedExpr) -> List[ResolvedColumn]:
    """Find direct parent columns referenced by an expression.
    
    Args:
        expression: Expression to analyze
        
    Returns:
        List of directly referenced ResolvedColumns
    """
```

## Supported SQL Features

### Statement Types
- ✅ SELECT
- ✅ CREATE TABLE AS SELECT
- ✅ CREATE VIEW
- ✅ INSERT
- ✅ UPDATE (with FROM clause)
- ✅ MERGE (MATCHED/NOT MATCHED)

### Query Features
- ✅ JOINs (INNER, LEFT, RIGHT, FULL, CROSS)
- ✅ Subqueries (in SELECT, FROM, WHERE)
- ✅ Common Table Expressions (WITH/CTE)
- ✅ UNION / UNION ALL / INTERSECT / EXCEPT
- ✅ Aggregate functions (SUM, COUNT, AVG, etc.)
- ✅ Window functions / Analytic functions
- ✅ CASE expressions
- ✅ STRUCT field access
- ✅ UNNEST / ARRAY operations

### Expression Handling
- ✅ Scalar functions (UPPER, LOWER, CONCAT, etc.)
- ✅ Mathematical expressions (+, -, *, /)
- ✅ Conditional logic (CASE, IF, COALESCE, NULLIF)
- ✅ Type casts
- ✅ Nested function calls

## Limitations

- Uses in-memory SimpleCatalog (no actual BigQuery connection)
- BigQuery SQL dialect only
- Requires explicit table schemas in catalog

## Development

### Adding New Tests

1. Add test case to appropriate test file
2. Run test: `pytest tests/test_module.py::test_name -v`
3. Implement feature to make test pass
4. Verify all tests still pass: `pytest`

### Porting from Java

Key differences between Java and Python ZetaSQL APIs:

| Java | Python |
|------|--------|
| `node.accept(visitor)` | `visitor.visit(node)` |
| `column.getId()` | `column.column_id` |
| `column.getName()` | `column.name` |
| `type.isStruct()` | `type.is_struct()` |
| `type.asStruct()` | `type.as_struct()` |
| `structType.getFieldList()` | `struct_type.field` |

## References

- [ZetaSQL Python](https://github.com/google/zetasql) - Official ZetaSQL Python bindings
- [zetasql-toolkit](https://github.com/GoogleCloudPlatform/zetasql-toolkit) - Original Java implementation
- [ZetaSQL Documentation](https://github.com/google/zetasql/blob/master/docs/README.md) - Language reference

## License

This project follows the Apache 2.0 license, consistent with the ZetaSQL toolkit.

## Contributing

This is a demonstration project for educational purposes. For production use cases, consider using the official zetasql-toolkit.

## Acknowledgments

- Based on GoogleCloudPlatform/zetasql-toolkit
- Uses Google's ZetaSQL for SQL analysis
- Inspired by BigQuery's SQL dialect and lineage capabilities
