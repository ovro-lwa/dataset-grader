import pandas as pd

from dataset_grader.summary import build_catalog_summary_plot, catalog_summary_table


def test_catalog_summary_table():
    catalog = pd.DataFrame(
        [
            {"day": "2024-12-28", "lst": "08h", "frequency": "74MHz"},
            {"day": "2024-12-28", "lst": "08h", "frequency": "82MHz"},
            {"day": "2024-12-28", "lst": "09h", "frequency": "74MHz"},
            {"day": "2024-12-29", "lst": "08h", "frequency": "74MHz"},
        ]
    )
    summary = catalog_summary_table(catalog)
    assert len(summary) == 3
    row = summary[(summary["day"] == "2024-12-28") & (summary["lst"] == "08h")].iloc[0]
    assert row["count"] == 2
    assert "74MHz" in row["subbands"]
    assert "82MHz" in row["subbands"]


def test_build_catalog_summary_plot():
    catalog = pd.DataFrame(
        [
            {"day": "2024-12-28", "lst": "08h", "frequency": "74MHz"},
            {"day": "2024-12-29", "lst": "09h", "frequency": "82MHz"},
        ]
    )
    plot = build_catalog_summary_plot(catalog)
    assert plot is not None
    assert len(plot.renderers) >= 1


def test_summary_empty_catalog():
    catalog = pd.DataFrame(columns=["day", "lst", "frequency"])
    assert catalog_summary_table(catalog).empty
    plot = build_catalog_summary_plot(catalog)
    assert plot.title.text == "Datasets per day and LST"
