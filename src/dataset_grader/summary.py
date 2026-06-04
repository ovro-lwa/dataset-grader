"""Bokeh summary heatmap: dataset count by day vs LST."""

from __future__ import annotations

import pandas as pd
from bokeh.models import ColumnDataSource, FixedTicker, HoverTool
from bokeh.palettes import Blues256
from bokeh.plotting import figure

from dataset_grader.grids import _axis_ticks, _cell_center, _freq_sort_key, _lst_sort_key

EMPTY_FILL = "#ffffff"
NONEMPTY_EDGE = "#424242"
NONEMPTY_EDGE_WIDTH = 0.5
MAX_SUBBAND_COUNT = 15


def count_to_fill_color(count: int, max_count: int = MAX_SUBBAND_COUNT) -> str:
    """Map subband count to fill: white at 0, light→dark blue for 1..max (capped)."""
    if count <= 0:
        return EMPTY_FILL
    capped = min(count, max_count)
    if max_count <= 1:
        return Blues256[128]
    idx = int((capped - 1) / (max_count - 1) * (len(Blues256) - 1))
    return Blues256[idx]


def _format_subbands(frequencies: pd.Series) -> str:
    unique = sorted(frequencies.unique(), key=_freq_sort_key)
    return ", ".join(str(f) for f in unique)


def catalog_summary_table(catalog: pd.DataFrame) -> pd.DataFrame:
    """Aggregate manifest/catalog rows by (day, lst).

    Returns columns: day, lst, count, subbands.
    """
    required = ("day", "lst", "frequency")
    missing = set(required) - set(catalog.columns)
    if missing:
        raise ValueError(f"Catalog missing columns: {sorted(missing)}")
    if catalog.empty:
        return pd.DataFrame(columns=["day", "lst", "count", "subbands"])

    grouped = (
        catalog.groupby(["day", "lst"], as_index=False)["frequency"]
        .agg(count="count", subbands=_format_subbands)
    )
    grouped["_lst_order"] = grouped["lst"].map(lambda v: _lst_sort_key(v)[0])
    return grouped.sort_values(["day", "_lst_order", "lst"]).drop(
        columns="_lst_order"
    ).reset_index(drop=True)


def build_catalog_summary_plot(
    catalog: pd.DataFrame,
    *,
    title: str = "Datasets per day and LST",
    width: int | None = None,
    height: int = 640,
) -> figure:
    """Heatmap of dataset counts; hover lists subband (frequency) names."""
    figure_kwargs: dict = {
        "title": title,
        "height": height,
        "x_axis_label": "LST",
        "y_axis_label": "Day",
        "sizing_mode": "scale_width",
    }
    if width is not None:
        figure_kwargs["width"] = width

    if catalog.empty:
        plot = figure(**figure_kwargs)
        plot.text(
            x=0,
            y=0,
            text=["No catalog data"],
            text_align="center",
            text_baseline="middle",
        )
        return plot

    summary = catalog_summary_table(catalog)
    if summary.empty:
        plot = figure(**figure_kwargs)
        plot.text(
            x=0,
            y=0,
            text=["No catalog data"],
            text_align="center",
            text_baseline="middle",
        )
        return plot

    day_labels = sorted(summary["day"].unique())
    lst_labels = sorted(summary["lst"].unique(), key=_lst_sort_key)
    n_days = len(day_labels)
    n_lst = len(lst_labels)
    day_index = {d: i for i, d in enumerate(day_labels)}
    lst_index = {lst: i for i, lst in enumerate(lst_labels)}

    xs: list[float] = []
    ys: list[float] = []
    counts: list[int] = []
    hovers: list[str] = []

    lookup = {
        (row.day, row.lst): (int(row.count), str(row.subbands))
        for row in summary.itertuples(index=False)
    }

    for day in day_labels:
        for lst in lst_labels:
            count, subbands = lookup.get((day, lst), (0, ""))
            xs.append(_cell_center(lst_index[lst]))
            ys.append(_cell_center(day_index[day]))
            counts.append(count)
            if count == 0:
                hovers.append(f"Day {day}\nLST {lst}\nDatasets: 0\nSubbands: (none)")
            else:
                hovers.append(
                    f"Day {day}\nLST {lst}\nDatasets: {count}\nSubbands: {subbands}"
                )

    cell_days: list[str] = []
    cell_lsts: list[str] = []
    fill_colors: list[str] = []
    line_colors: list[str] = []
    line_widths: list[float] = []
    for day in day_labels:
        for lst in lst_labels:
            cell_days.append(day)
            cell_lsts.append(lst)

    for count in counts:
        fill_colors.append(count_to_fill_color(count))
        if count > 0:
            line_colors.append(NONEMPTY_EDGE)
            line_widths.append(NONEMPTY_EDGE_WIDTH)
        else:
            line_colors.append(EMPTY_FILL)
            line_widths.append(0.0)

    source = ColumnDataSource(
        data={
            "x": xs,
            "y": ys,
            "count": counts,
            "hover_text": hovers,
            "day": cell_days,
            "lst": cell_lsts,
            "fill_color": fill_colors,
            "line_color": line_colors,
            "line_width": line_widths,
        }
    )

    plot = figure(
        **figure_kwargs,
        x_range=(0, n_lst),
        y_range=(0, n_days),
        tools="reset",
        toolbar_location="above",
    )
    plot.rect(
        x="x",
        y="y",
        width=1.0,
        height=1.0,
        source=source,
        fill_color="fill_color",
        line_color="line_color",
        line_width="line_width",
    )
    hover_renderer = plot.rect(
        x="x",
        y="y",
        width=1.0,
        height=1.0,
        source=source,
        fill_alpha=0,
        line_width=0,
        hover_fill_alpha=0,
        hover_line_alpha=0,
    )
    plot.grid.grid_line_color = None
    plot.add_tools(
        HoverTool(
            renderers=[hover_renderer],
            tooltips="@hover_text{safe}",
        )
    )

    x_ticks, x_overrides = _axis_ticks(n_lst, lst_labels)
    y_ticks, y_overrides = _axis_ticks(n_days, day_labels)
    plot.xaxis.ticker = FixedTicker(ticks=x_ticks)
    plot.yaxis.ticker = FixedTicker(ticks=y_ticks)
    plot.xaxis.major_label_overrides = x_overrides
    plot.yaxis.major_label_overrides = y_overrides
    plot.xaxis.axis_label = "LST"
    plot.yaxis.axis_label = "Day"

    return plot
