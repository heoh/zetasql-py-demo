"""Sample catalog creation for testing and demos.

Creates a BigQuery-style catalog with sample tables using
project.dataset.table naming convention.
"""

from zetasql.api import CatalogBuilder, TableBuilder
from zetasql.types import SimpleCatalog, TypeKind, LanguageOptions, ZetaSQLBuiltinFunctionOptions

from ..options import get_bigquery_language_options


def create_sample_catalog() -> SimpleCatalog:
    """Create a sample catalog with BigQuery-style tables.
    
    Creates a catalog with the following tables:
    - project1.dataset1.orders (order_id, customer_id, amount, order_date)
    - project1.dataset1.customers (customer_id, name, email, region)
    - project1.dataset1.products (product_id, name, price, category)
    - project1.dataset1.order_items (order_id, product_id, quantity, price)
    
    All tables use BigQuery 3-part naming: project.dataset.table
    Includes builtin functions for BigQuery SQL compatibility.
    
    Returns:
        SimpleCatalog configured with sample tables and builtin functions
    """
    # Create orders table
    orders_table = (
        TableBuilder("project1.dataset1.orders")
        .add_column("order_id", TypeKind.TYPE_INT64)
        .add_column("customer_id", TypeKind.TYPE_INT64)
        .add_column("amount", TypeKind.TYPE_DOUBLE)
        .add_column("order_date", TypeKind.TYPE_DATE)
        .build()
    )
    
    # Create customers table
    customers_table = (
        TableBuilder("project1.dataset1.customers")
        .add_column("customer_id", TypeKind.TYPE_INT64)
        .add_column("name", TypeKind.TYPE_STRING)
        .add_column("email", TypeKind.TYPE_STRING)
        .add_column("region", TypeKind.TYPE_STRING)
        .build()
    )
    
    # Create products table
    products_table = (
        TableBuilder("project1.dataset1.products")
        .add_column("product_id", TypeKind.TYPE_INT64)
        .add_column("name", TypeKind.TYPE_STRING)
        .add_column("price", TypeKind.TYPE_DOUBLE)
        .add_column("category", TypeKind.TYPE_STRING)
        .build()
    )
    
    # Create order_items table
    order_items_table = (
        TableBuilder("project1.dataset1.order_items")
        .add_column("order_id", TypeKind.TYPE_INT64)
        .add_column("product_id", TypeKind.TYPE_INT64)
        .add_column("quantity", TypeKind.TYPE_INT64)
        .add_column("price", TypeKind.TYPE_DOUBLE)
        .build()
    )
    
    # Get BigQuery language options for builtin functions
    lang_opts = get_bigquery_language_options()
    builtin_opts = ZetaSQLBuiltinFunctionOptions(language_options=lang_opts)
    
    # Build catalog with all tables and builtin functions
    catalog = (
        CatalogBuilder("sample_catalog")
        .add_table(orders_table)
        .add_table(customers_table)
        .add_table(products_table)
        .add_table(order_items_table)
        .with_builtin_functions(builtin_opts)
        .build()
    )
    
    return catalog
