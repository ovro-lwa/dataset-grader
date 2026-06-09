import pandas as pd

from dataset_grader.summary import (
    build_catalog_summary_plot,
    build_good_summary_plot,
    catalog_summary_table,
    count_to_fill_color,
    good_summary_table,
)


def test_count_to_fill_color_orders_light_to_dark():
    light = count_to_fill_color(1, 5)
    dark = count_to_fill_color(5, 5)
    assert light != dark
    from bokeh.palettes import Blues256

    # In Bokeh's Blues256, higher index is lighter blue.
    assert Blues256.index(light) > Blues256.index(dark)


def test_count_to_fill_color_zero_is_white():
    assert count_to_fill_color(0, 10) == "#ffffff"


def test_count_to_fill_color_caps_at_max():
    from dataset_grader.summary import MAX_SUBBAND_COUNT

    at_max = count_to_fill_color(MAX_SUBBAND_COUNT)
    above_max = count_to_fill_color(MAX_SUBBAND_COUNT + 10)
    assert at_max == above_max


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


def test_good_summary_table():
    datasets = pd.DataFrame(
        [
            {"dataset_id": 1, "day": "2024-12-28", "lst": "08h", "frequency": "74MHz"},
            {"dataset_id": 2, "day": "2024-12-28", "lst": "08h", "frequency": "82MHz"},
            {"dataset_id": 3, "day": "2024-12-28", "lst": "09h", "frequency": "74MHz"},
        ]
    )
    grades = pd.DataFrame(
        [
            {"dataset_id": 1, "user_name": "alice", "grade": "pass"},
            {"dataset_id": 1, "user_name": "bob", "grade": "pass"},
            {"dataset_id": 2, "user_name": "alice", "grade": "pass"},
            {"dataset_id": 2, "user_name": "bob", "grade": "retry"},
            {"dataset_id": 3, "user_name": "alice", "grade": "fail"},
        ]
    )
    summary = good_summary_table(datasets, grades)
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["day"] == "2024-12-28"
    assert row["lst"] == "08h"
    assert row["count"] == 1
    assert row["subbands"] == "74MHz"


def test_build_good_summary_plot():
    datasets = pd.DataFrame(
        [
            {"dataset_id": 1, "day": "2024-12-28", "lst": "08h", "frequency": "74MHz"},
            {"dataset_id": 2, "day": "2024-12-29", "lst": "09h", "frequency": "82MHz"},
        ]
    )
    grades = pd.DataFrame(
        [
            {"dataset_id": 1, "user_name": "alice", "grade": "pass"},
            {"dataset_id": 2, "user_name": "alice", "grade": "retry"},
        ]
    )
    plot = build_good_summary_plot(datasets, grades)
    assert plot is not None
    assert len(plot.renderers) >= 1
