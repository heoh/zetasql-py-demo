"""Tests for lineage result formatters."""

import json
import pytest

from zetasql_demo.lineage import (
    ColumnEntity,
    ColumnLineage,
    TableLineage,
    LineageFormatter,
)


class TestTableLineageFormatting:
    """Tests for table lineage formatting."""
    
    def test_table_lineage_to_json(self):
        """Test table lineage JSON serialization."""
        lineage = TableLineage(
            target="project.dataset.target",
            sources={"project.dataset.source1", "project.dataset.source2"},
            statement_type="INSERT"
        )
        
        result = LineageFormatter.to_json(lineage)
        data = json.loads(result)
        
        assert data["target"] == "project.dataset.target"
        assert "project.dataset.source1" in data["sources"]
        assert "project.dataset.source2" in data["sources"]
        assert data["statement_type"] == "INSERT"
    
    def test_table_lineage_to_text(self):
        """Test table lineage text formatting."""
        lineage = TableLineage(
            target="project.dataset.target",
            sources={"project.dataset.source1", "project.dataset.source2"},
            statement_type="INSERT"
        )
        
        result = LineageFormatter.to_text(lineage)
        
        assert "INSERT" in result
        assert "project.dataset.target" in result
        assert "project.dataset.source1" in result
        assert "project.dataset.source2" in result
    
    def test_table_lineage_select_no_target(self):
        """Test SELECT statement with no target."""
        lineage = TableLineage(
            target=None,
            sources={"project.dataset.source1"},
            statement_type="SELECT"
        )
        
        text = LineageFormatter.to_text(lineage)
        json_str = LineageFormatter.to_json(lineage)
        data = json.loads(json_str)
        
        assert "SELECT" in text
        assert data["target"] is None
        assert "project.dataset.source1" in data["sources"]


class TestColumnLineageFormatting:
    """Tests for column lineage formatting."""
    
    def test_column_lineage_to_json(self):
        """Test column lineage JSON serialization."""
        target = ColumnEntity("target_table", "result_col")
        parents = {
            ColumnEntity("source1", "col1"),
            ColumnEntity("source2", "col2"),
        }
        lineage = ColumnLineage(target, parents)
        
        result = LineageFormatter.to_json([lineage])
        data = json.loads(result)
        
        assert len(data) == 1
        assert data[0]["target"]["table"] == "target_table"
        assert data[0]["target"]["column"] == "result_col"
        assert len(data[0]["parents"]) == 2
    
    def test_column_lineage_to_text(self):
        """Test column lineage text formatting."""
        target = ColumnEntity("target_table", "result_col")
        parents = {
            ColumnEntity("source1", "col1"),
            ColumnEntity("source2", "col2"),
        }
        lineage = ColumnLineage(target, parents)
        
        result = LineageFormatter.to_text([lineage])
        
        assert "target_table.result_col" in result
        assert "source1.col1" in result
        assert "source2.col2" in result
        assert "<-" in result
    
    def test_column_lineage_no_parents(self):
        """Test column with no parents (literal or constant)."""
        target = ColumnEntity("target_table", "constant_col")
        lineage = ColumnLineage(target, set())
        
        result = LineageFormatter.to_text([lineage])
        
        assert "target_table.constant_col" in result
        assert "(no parent columns)" in result.lower() or "literal" in result.lower()
    
    def test_multiple_column_lineages(self):
        """Test formatting multiple column lineages."""
        lineages = [
            ColumnLineage(
                ColumnEntity("target", "col1"),
                {ColumnEntity("source1", "a")}
            ),
            ColumnLineage(
                ColumnEntity("target", "col2"),
                {ColumnEntity("source2", "b"), ColumnEntity("source2", "c")}
            ),
        ]
        
        result = LineageFormatter.to_text(lineages)
        
        assert "target.col1" in result
        assert "target.col2" in result
        assert "source1.a" in result
        assert "source2.b" in result
        assert "source2.c" in result


class TestEmptyLineage:
    """Tests for empty lineage formatting."""
    
    def test_empty_sources(self):
        """Test table lineage with empty sources."""
        lineage = TableLineage(
            target="project.dataset.target",
            sources=set(),
            statement_type="CREATE_TABLE"
        )
        
        text = LineageFormatter.to_text(lineage)
        json_str = LineageFormatter.to_json(lineage)
        
        assert "CREATE_TABLE" in text
        assert json_str  # Should not error
    
    def test_empty_column_lineage_list(self):
        """Test empty column lineage list."""
        result_text = LineageFormatter.to_text([])
        result_json = LineageFormatter.to_json([])
        
        assert result_text  # Should return something
        assert result_json == "[]"
