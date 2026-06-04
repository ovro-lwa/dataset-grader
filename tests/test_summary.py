import pandas as pd

from dataset_grader.summary import (
    build_catalog_summary_plot,
    catalog_summary_table,
    count_to_fill_color,
)


def test_count_to_fill_color_orders_light_to_dark():
    light = count_to_fill_color(1, 5)
    dark = count_to_fill_color(5, 5)
    assert light != dark
    # Blues256 increases in darkness with index
    from bokeh.palettes import Blues256

    assert Blues256.index(light) < Blues256.index(dark)


def test_count_to_fill_color_zero_is_white():
    assert count_to_fill_color(0, 10) == "#ffffff"


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
