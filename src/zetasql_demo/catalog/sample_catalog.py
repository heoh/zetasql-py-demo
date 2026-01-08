"""Sample catalog creation for testing and demos.

Creates BigQuery-style tables with project.dataset.table naming convention.
"""

from zetasql.api import CatalogBuilder, TableBuilder
from zetasql.types import (
    LanguageOptions,
    SimpleCatalog,
    TypeKind,
    ZetaSQLBuiltinFunctionOptions,
)


def create_sample_catalog(language_options: LanguageOptions) -> SimpleCatalog:
    """Create a sample catalog with BigQuery-style test tables.
    
    Creates four sample tables with project.dataset.table naming:
    - project1.dataset1.orders (order_id, customer_id, amount, order_date)
    - project1.dataset1.customers (customer_id, name, email, region)
    - project1.dataset1.products (product_id, name, price, category)
    - project1.dataset1.order_items (order_id, product_id, quantity, price)
    
    Args:
        language_options: LanguageOptions for builtin functions configuration
        
    Returns:
        SimpleCatalog configured with sample tables and builtin functions
        
    Example:
        >>> from zetasql_demo.options import get_bigquery_language_options
        >>> lang_opts = get_bigquery_language_options()
        >>> catalog = create_sample_catalog(lang_opts)
        >>> len(catalog.table)
        4
    """
    # orders table
    orders_table = (
        TableBuilder("project1.dataset1.orders")
        .add_column("order_id", TypeKind.TYPE_INT64)
        .add_column("customer_id", TypeKind.TYPE_INT64)
        .add_column("amount", TypeKind.TYPE_DOUBLE)
        .add_column("order_date", TypeKind.TYPE_DATE)
        .build()
    )
    
    # customers table
    customers_table = (
        TableBuilder("project1.dataset1.customers")
        .add_column("customer_id", TypeKind.TYPE_INT64)
        .add_column("name", TypeKind.TYPE_STRING)
        .add_column("email", TypeKind.TYPE_STRING)
        .add_column("region", TypeKind.TYPE_STRING)
        .build()
    )
    
    # products table
    products_table = (
        TableBuilder("project1.dataset1.products")
        .add_column("product_id", TypeKind.TYPE_INT64)
        .add_column("name", TypeKind.TYPE_STRING)
        .add_column("price", TypeKind.TYPE_DOUBLE)
        .add_column("category", TypeKind.TYPE_STRING)
        .build()
    )
    
    # order_items table
    order_items_table = (
        TableBuilder("project1.dataset1.order_items")
        .add_column("order_id", TypeKind.TYPE_INT64)
        .add_column("product_id", TypeKind.TYPE_INT64)
        .add_column("quantity", TypeKind.TYPE_INT64)
        .add_column("price", TypeKind.TYPE_DOUBLE)
        .build()
    )
    
    # Build catalog with builtin functions
    builtin_opts = ZetaSQLBuiltinFunctionOptions(
        language_options=language_options
    )
    
    catalog = (
        CatalogBuilder("test_catalog")
        .add_table(orders_table)
        .add_table(customers_table)
        .add_table(products_table)
        .add_table(order_items_table)
        .with_builtin_functions(builtin_opts)
        .build()
    )
    
    return catalog
