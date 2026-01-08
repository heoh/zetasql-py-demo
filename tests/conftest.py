"""pytest configuration and shared fixtures."""

import pytest
from zetasql.api import Analyzer
from zetasql.types import (
    AnalyzerOptions,
    LanguageOptions,
    SimpleCatalog,
)

from zetasql_demo.options import get_bigquery_language_options
from zetasql_demo.catalog import create_sample_catalog
from zetasql_demo.catalog import create_sample_catalog


@pytest.fixture
def bigquery_language_options() -> LanguageOptions:
    """BigQuery-compatible language options.
    
    Returns:
        LanguageOptions configured for BigQuery SQL dialect
    """
    return get_bigquery_language_options()


@pytest.fixture
def sample_catalog(bigquery_language_options: LanguageOptions) -> SimpleCatalog:
    """Create a sample catalog with test tables.
    
    Uses create_sample_catalog() to create BigQuery-style tables.
    
    Args:
        bigquery_language_options: Language options for builtin functions
        
    Returns:
        SimpleCatalog with sample tables
    """
    return create_sample_catalog(bigquery_language_options)


@pytest.fixture
def analyzer(
    bigquery_language_options: LanguageOptions,
    sample_catalog: SimpleCatalog
) -> Analyzer:
    """Create an analyzer with BigQuery options and sample catalog.
    
    Args:
        bigquery_language_options: Language options
        sample_catalog: Sample catalog with tables
        
    Returns:
        Configured Analyzer instance
    """
    options = AnalyzerOptions(language_options=bigquery_language_options)
    return Analyzer(options, sample_catalog)
