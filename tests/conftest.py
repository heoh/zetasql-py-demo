"""pytest configuration and shared fixtures for ZetaSQL lineage demo tests."""

import pytest
from zetasql.api import Analyzer, CatalogBuilder, TableBuilder
from zetasql.types import AnalyzerOptions, LanguageOptions, SimpleCatalog, ZetaSQLBuiltinFunctionOptions

from zetasql_demo.options import get_bigquery_language_options


@pytest.fixture
def bigquery_language_options() -> LanguageOptions:
    """BigQuery-compatible LanguageOptions fixture.
    
    Returns:
        LanguageOptions configured for BigQuery SQL dialect
    """
    return get_bigquery_language_options()


@pytest.fixture
def sample_catalog(bigquery_language_options: LanguageOptions) -> SimpleCatalog:
    """Sample catalog with test tables fixture.
    
    Will be implemented after sample_catalog.py is created.
    
    Args:
        bigquery_language_options: Language options for builtin functions
        
    Returns:
        SimpleCatalog with sample tables for testing
    """
    from zetasql_demo.catalog import create_sample_catalog
    return create_sample_catalog()


@pytest.fixture
def analyzer(sample_catalog: SimpleCatalog, bigquery_language_options: LanguageOptions) -> Analyzer:
    """Analyzer fixture configured with sample catalog and BigQuery options.
    
    Args:
        sample_catalog: Sample catalog with test tables
        bigquery_language_options: BigQuery language options
        
    Returns:
        Analyzer ready for SQL analysis
    """
    options = AnalyzerOptions(language_options=bigquery_language_options)
    return Analyzer(options, sample_catalog)
