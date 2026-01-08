"""Sample catalog creation for demonstrations.

Creates a BigQuery-style catalog with sample tables without
requiring actual BigQuery connection.
"""

from zetasql.api import CatalogBuilder, TableBuilder
from zetasql.types import (
    LanguageOptions,
    SimpleCatalog,
    TypeKind,
    ZetaSQLBuiltinFunctionOptions,
)
from ..options.bigquery_options import get_bigquery_language_options


def create_sample_catalog() -> SimpleCatalog:
    """Create sample catalog with BigQuery-style tables.
    
    Creates the following tables in catalog 'myproject':
    - orders: Order transaction data
    - customers: Customer information
    - products: Product catalog
    
    Returns:
        SimpleCatalog with sample tables and BigQuery builtin functions
    """
    # Create orders table
    orders = (
        TableBuilder("orders")
        .add_column("order_id", TypeKind.TYPE_INT64)
        .add_column("customer_id", TypeKind.TYPE_INT64)
        .add_column("product_id", TypeKind.TYPE_INT64)
        .add_column("quantity", TypeKind.TYPE_INT64)
        .add_column("amount", TypeKind.TYPE_DOUBLE)
        .add_column("order_date", TypeKind.TYPE_DATE)
        .build()
    )
    
    # Create customers table
    customers = (
        TableBuilder("customers")
        .add_column("customer_id", TypeKind.TYPE_INT64)
        .add_column("name", TypeKind.TYPE_STRING)
        .add_column("email", TypeKind.TYPE_STRING)
        .add_column("country", TypeKind.TYPE_STRING)
        .build()
    )
    
    # Create products table
    products = (
        TableBuilder("products")
        .add_column("product_id", TypeKind.TYPE_INT64)
        .add_column("name", TypeKind.TYPE_STRING)
        .add_column("price", TypeKind.TYPE_DOUBLE)
        .add_column("category", TypeKind.TYPE_STRING)
        .build()
    )
    
    # Get BigQuery language options for builtin functions
    lang_opts = get_bigquery_language_options()
    builtin_opts = ZetaSQLBuiltinFunctionOptions(language_options=lang_opts)
    
    # Build catalog with all tables and builtin functions
    catalog = (
        CatalogBuilder("myproject")
        .add_table(orders)
        .add_table(customers)
        .add_table(products)
        .with_builtin_functions(builtin_opts)
        .build()
    )
    
    return catalog
