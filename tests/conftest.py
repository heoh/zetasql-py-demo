"""Pytest configuration and shared fixtures."""

import pytest
from zetasql.api import Analyzer, CatalogBuilder, TableBuilder
from zetasql.types import (
    AnalyzerOptions,
    LanguageOptions,
    SimpleCatalog,
    TypeKind,
    ZetaSQLBuiltinFunctionOptions,
)


@pytest.fixture
def language_options() -> LanguageOptions:
    """Provide LanguageOptions with maximum features.
    
    Returns:
        Configured LanguageOptions
    """
    return LanguageOptions.maximum_features()


@pytest.fixture
def sample_catalog(language_options: LanguageOptions) -> SimpleCatalog:
    """Provide a sample catalog with tables for testing.
    
    Tables created (in catalog 'myproject'):
    - orders
    - customers  
    - products
    
    Args:
        language_options: Language options for builtin functions
        
    Returns:
        SimpleCatalog with sample tables
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
    
    # Build catalog with builtin functions
    builtin_opts = ZetaSQLBuiltinFunctionOptions(language_options=language_options)
    
    catalog = (
        CatalogBuilder("myproject")
        .add_table(orders)
        .add_table(customers)
        .add_table(products)
        .with_builtin_functions(builtin_opts)
        .build()
    )
    
    return catalog


@pytest.fixture
def analyzer(language_options: LanguageOptions, sample_catalog: SimpleCatalog) -> Analyzer:
    """Provide configured Analyzer instance.
    
    Args:
        language_options: Language options
        sample_catalog: Sample catalog
        
    Returns:
        Analyzer instance
    """
    options = AnalyzerOptions(language_options=language_options)
    return Analyzer(options, sample_catalog)
