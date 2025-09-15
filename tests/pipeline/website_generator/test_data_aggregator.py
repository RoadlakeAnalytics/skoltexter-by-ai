"""Tests for data aggregation functions in program3_generate_website.
"""

import pandas as pd

import src.program3_generate_website as p3

def test_read_school_csv_bad_columns(tmp_path):
    csvp = tmp_path / "bad.csv"
    csvp.write_text("A;B\n1;2\n", encoding="utf-8")
    df = p3.read_school_csv(csvp)
    assert df.empty

