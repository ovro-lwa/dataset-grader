"""Bokeh LST × frequency grading grids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
from bokeh.events import Tap
from bokeh.models import ColumnDataSource, FixedTicker, HoverTool
from bokeh.plotting import figure

from dataset_grader.aggregate import (
    PERSONAL_COLORS,
    consensus_fill,
    format_hover_lines,
)

def _lst_sort_key(lst: str) -> tuple[int, str]:
    text = lst.strip().lower()
    if text.endswith("h") and text[:-1].isdigit():
        return (int(text[:-1]), lst)
    return (0, lst)


def _freq_sort_key(freq: str) -> tuple[float, str]:
    text = freq.strip()
    if text.lower().endswith("mhz"):
        try:
            return (float(text[:-3]), freq)
        except ValueError:
            pass
    return (0.0, freq)


def build_axis_layout(datasets: pd.DataFrame) -> tuple[list[str], list[str], dict[tuple[str, str], int]]:
    """Return sorted LST labels, frequency labels, and (lst, frequency) -> dataset_id."""
    lst_labels = sorted(datasets["lst"].unique(), key=_lst_sort_key)
    freq_labels = sorted(datasets["frequency"].unique(), key=_freq_sort_key)
    lookup: dict[tuple[str, str], int] = {}
    for row in datasets.itertuples(index=False):
        lookup[(row.lst, row.frequency)] = int(row.dataset_id)
    return lst_labels, freq_labels, lookup


def _cell_center(idx: int) -> float:
    return idx + 0.5


def _index_from_coord(coord: float, n: int) -> int:
    idx = int(coord)
    if idx < 0:
        return 0
    if idx >= n:
        return n - 1
    return idx


@dataclass
class GridGeometry:
    lst_labels: list[str]
    freq_labels: list[str]
    lookup: dict[tuple[str, str], int]
    n_lst: int
    n_freq: int

    @classmethod
    def from_datasets(cls, datasets: pd.DataFrame) -> GridGeometry:
        lst_labels, freq_labels, lookup = build_axis_layout(datasets)
        return cls(
            lst_labels=lst_labels,
            freq_labels=freq_labels,
            lookup=lookup,
            n_lst=len(lst_labels),
            n_freq=len(freq_labels),
        )

    def dataset_id_at(self, lst_idx: int, freq_idx: int) -> int | None:
        if lst_idx < 0 or freq_idx < 0:
            return None
        if lst_idx >= self.n_lst or freq_idx >= self.n_freq:
            return None
        lst = self.lst_labels[lst_idx]
        freq = self.freq_labels[freq_idx]
        return self.lookup.get((lst, freq))

    def indices_for_dataset(self, dataset_id: int) -> tuple[int, int] | None:
        for (lst, freq), ds_id in self.lookup.items():
            if ds_id == dataset_id:
                return self.lst_labels.index(lst), self.freq_labels.index(freq)
        return None


def _axis_ticks(n: int, labels: list[str]) -> tuple[list[float], dict[float, str]]:
    ticks = [_cell_center(i) for i in range(n)]
    overrides = {ticks[i]: labels[i] for i in range(n)}
    return ticks, overrides


def _build_cell_source(
    geometry: GridGeometry,
    *,
    fill_color: Callable[[str, str], str],
    hover_text: Callable[[str, str], str],
) -> ColumnDataSource:
    xs: list[float] = []
    ys: list[float] = []
    colors: list[str] = []
    hovers: list[str] = []
    dataset_ids: list[int | None] = []
    lst_names: list[str] = []
    freq_names: list[str] = []

    for lst_idx, lst in enumerate(geometry.lst_labels):
        for freq_idx, freq in enumerate(geometry.freq_labels):
            xs.append(_cell_center(lst_idx))
            ys.append(_cell_center(freq_idx))
            lst_names.append(lst)
            freq_names.append(freq)
            colors.append(fill_color(lst, freq))
            hovers.append(hover_text(lst, freq))
            dataset_ids.append(geometry.lookup.get((lst, freq)))

    return ColumnDataSource(
        data={
            "x": xs,
            "y": ys,
            "fill_color": colors,
            "hover_text": hovers,
            "dataset_id": dataset_ids,
            "lst": lst_names,
            "frequency": freq_names,
        }
    )


def build_personal_grid(
    geometry: GridGeometry,
    user_grades: dict[int, str],
    *,
    on_tap: Callable[[int], None] | None = None,
    grading_enabled: bool = True,
    title: str = "Your grades",
) -> figure:
    def fill(lst: str, freq: str) -> str:
        ds_id = geometry.lookup.get((lst, freq))
        if ds_id is None:
            return PERSONAL_COLORS[None]
        return PERSONAL_COLORS.get(user_grades.get(ds_id), PERSONAL_COLORS[None])

    def hover(lst: str, freq: str) -> str:
        ds_id = geometry.lookup.get((lst, freq))
        if ds_id is None:
            return "No dataset"
        grade = user_grades.get(ds_id)
        if grading_enabled:
            action = "Click cell to cycle: unset → pass → fail → retry"
        else:
            action = "Sign in to grade cells"
        return (
            f"LST {lst}, {freq}\n"
            f"Your grade: {grade or 'unset'}\n"
            f"{action}"
        )

    source = _build_cell_source(geometry, fill_color=fill, hover_text=hover)
    tools = "tap,reset" if grading_enabled and on_tap is not None else "hover,reset"
    plot = figure(
        title=title,
        width=700,
        height=400,
        x_range=(0, geometry.n_lst),
        y_range=(0, geometry.n_freq),
        tools=tools,
        active_tap="tap" if grading_enabled and on_tap is not None else None,
    )
    plot.rect(
        x="x",
        y="y",
        width=0.95,
        height=0.95,
        source=source,
        fill_color="fill_color",
        line_color="#424242",
        line_width=0.5,
    )
    hover_renderer = plot.rect(
        x="x",
        y="y",
        width=0.95,
        height=0.95,
        source=source,
        fill_alpha=0,
        line_alpha=0,
        hover_fill_alpha=0,
        hover_line_alpha=0,
    )
    plot.add_tools(
        HoverTool(
            renderers=[hover_renderer],
            tooltips=[("Info", "@hover_text{safe}")],
        )
    )
    x_ticks, x_overrides = _axis_ticks(geometry.n_lst, geometry.lst_labels)
    y_ticks, y_overrides = _axis_ticks(geometry.n_freq, geometry.freq_labels)
    plot.xaxis.ticker = FixedTicker(ticks=x_ticks)
    plot.yaxis.ticker = FixedTicker(ticks=y_ticks)
    plot.xaxis.major_label_overrides = x_overrides
    plot.yaxis.major_label_overrides = y_overrides
    plot.xaxis.axis_label = "LST"
    plot.yaxis.axis_label = "Frequency"

    if grading_enabled and on_tap is not None:

        def on_tap_event(event: Tap) -> None:
            if event.x is None or event.y is None:
                return
            lst_idx = _index_from_coord(event.x, geometry.n_lst)
            freq_idx = _index_from_coord(event.y, geometry.n_freq)
            ds_id = geometry.dataset_id_at(lst_idx, freq_idx)
            if ds_id is not None:
                on_tap(ds_id)

        plot.on_event(Tap, on_tap_event)
    plot._grader_source = source  # type: ignore[attr-defined]
    return plot


def build_consensus_grid(
    geometry: GridGeometry,
    grades_by_dataset: dict[int, list[tuple[str, str]]],
    *,
    title: str = "All reviewers",
) -> figure:
    def fill(lst: str, freq: str) -> str:
        ds_id = geometry.lookup.get((lst, freq))
        if ds_id is None:
            return PERSONAL_COLORS[None]
        entries = grades_by_dataset.get(ds_id, [])
        return consensus_fill(g for _, g in entries)

    def hover(lst: str, freq: str) -> str:
        ds_id = geometry.lookup.get((lst, freq))
        if ds_id is None:
            return "No dataset"
        entries = grades_by_dataset.get(ds_id, [])
        header = f"LST {lst}, {freq}"
        body = format_hover_lines(entries)
        return f"{header}\n{body}"

    source = _build_cell_source(geometry, fill_color=fill, hover_text=hover)
    plot = figure(
        title=title,
        width=700,
        height=400,
        x_range=(0, geometry.n_lst),
        y_range=(0, geometry.n_freq),
        tools="reset",
    )
    plot.rect(
        x="x",
        y="y",
        width=0.95,
        height=0.95,
        source=source,
        fill_color="fill_color",
        line_color="#424242",
        line_width=0.5,
    )
    hover_renderer = plot.rect(
        x="x",
        y="y",
        width=0.95,
        height=0.95,
        source=source,
        fill_alpha=0,
        line_alpha=0,
        hover_fill_alpha=0,
        hover_line_alpha=0,
    )
    plot.add_tools(
        HoverTool(
            renderers=[hover_renderer],
            tooltips="@hover_text{safe}",
        )
    )
    x_ticks, x_overrides = _axis_ticks(geometry.n_lst, geometry.lst_labels)
    y_ticks, y_overrides = _axis_ticks(geometry.n_freq, geometry.freq_labels)
    plot.xaxis.ticker = FixedTicker(ticks=x_ticks)
    plot.yaxis.ticker = FixedTicker(ticks=y_ticks)
    plot.xaxis.major_label_overrides = x_overrides
    plot.yaxis.major_label_overrides = y_overrides
    plot.xaxis.axis_label = "LST"
    plot.yaxis.axis_label = "Frequency"
    plot._grader_source = source  # type: ignore[attr-defined]
    return plot


def update_personal_grid_colors(plot: figure, geometry: GridGeometry, user_grades: dict[int, str]) -> None:
    source: ColumnDataSource = plot._grader_source  # type: ignore[attr-defined]
    colors = []
    hovers = []
    for lst, freq, ds_id in zip(
        source.data["lst"],
        source.data["frequency"],
        source.data["dataset_id"],
        strict=True,
    ):
        if ds_id is None:
            colors.append(PERSONAL_COLORS[None])
            hovers.append("No dataset")
        else:
            grade = user_grades.get(int(ds_id))
            colors.append(PERSONAL_COLORS.get(grade, PERSONAL_COLORS[None]))
            hovers.append(
                f"LST {lst}, {freq}\n"
                f"Your grade: {grade or 'unset'}\n"
                "Click cell to cycle: unset → pass → fail → retry"
            )
    source.data["fill_color"] = colors
    source.data["hover_text"] = hovers


def update_consensus_grid_colors(
    plot: figure,
    geometry: GridGeometry,
    grades_by_dataset: dict[int, list[tuple[str, str]]],
) -> None:
    source: ColumnDataSource = plot._grader_source  # type: ignore[attr-defined]
    colors = []
    hovers = []
    for lst, freq, ds_id in zip(
        source.data["lst"],
        source.data["frequency"],
        source.data["dataset_id"],
        strict=True,
    ):
        if ds_id is None:
            colors.append(PERSONAL_COLORS[None])
            hovers.append("No dataset")
        else:
            entries = grades_by_dataset.get(int(ds_id), [])
            colors.append(consensus_fill(g for _, g in entries))
            header = f"LST {lst}, {freq}"
            body = format_hover_lines(entries)
            hovers.append(f"{header}\n{body}")
    source.data["fill_color"] = colors
    source.data["hover_text"] = hovers


def grades_by_dataset_from_df(grades_df: pd.DataFrame) -> dict[int, list[tuple[str, str]]]:
    result: dict[int, list[tuple[str, str]]] = {}
    if grades_df.empty:
        return result
    for row in grades_df.itertuples(index=False):
        ds_id = int(row.dataset_id)
        result.setdefault(ds_id, []).append((str(row.user_name), str(row.grade)))
    return result
