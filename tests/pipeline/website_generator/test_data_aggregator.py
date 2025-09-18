"""Tests for data aggregation functions in website generator package."""

from src.pipeline.website_generator import data_aggregator as p3


def test_read_school_csv_bad_columns(tmp_path):
    csvp = tmp_path / "bad.csv"
    csvp.write_text("A;B\n1;2\n", encoding="utf-8")
    df = p3.read_school_csv(csvp)
    assert df.empty
