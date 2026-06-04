"""Panel application for collaborative dataset grading."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import panel as pn
import param
from bokeh.plotting import figure

from dataset_grader.config import GraderConfig, next_grade
from dataset_grader.db import GraderDatabase, User
from dataset_grader.discovery import discover_catalog
from dataset_grader.users import ensure_allowed_user, load_user_names
from dataset_grader.grids import (
    GridGeometry,
    build_consensus_grid,
    build_personal_grid,
    grades_by_dataset_from_df,
    update_consensus_grid_colors,
    update_personal_grid_colors,
)
from dataset_grader.summary import build_catalog_summary_plot

logger = logging.getLogger(__name__)

pn.extension("tabulator", sizing_mode="stretch_width")

_SESSION_USER_KEY = "grader_user"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_manifest_path() -> Path | None:
    candidate = _repo_root() / "example" / "manifest.csv"
    return candidate if candidate.is_file() else None


def _default_users_path() -> Path | None:
    for candidate in (
        _repo_root() / "config" / "users.json",
        _repo_root() / "example" / "users.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def _load_config() -> GraderConfig:
    config = GraderConfig.from_env()
    manifest_path = config.manifest_path
    if config.discovery_mode == "manifest" and manifest_path is None:
        manifest_path = _default_manifest_path()
    users_path = config.users_path
    if not users_path.is_file():
        users_path = _default_users_path() or users_path
    if manifest_path != config.manifest_path or users_path != config.users_path:
        return GraderConfig(
            db_path=config.db_path,
            discovery_mode=config.discovery_mode,
            manifest_path=manifest_path,
            data_root=config.data_root,
            users_path=users_path,
            host=config.host,
            port=config.port,
        )
    return config


def _get_session_user() -> User | None:
    user = getattr(pn.state, _SESSION_USER_KEY, None)
    return user


def _set_session_user(user: User | None) -> None:
    setattr(pn.state, _SESSION_USER_KEY, user)


class DatasetGraderApp(param.Parameterized):
    day = param.Selector(default=None, objects=[], allow_None=True)

    def __init__(self, **params):
        super().__init__(**params)
        self._config = _load_config()
        self._reviewer_names = load_user_names(self._config.users_path)
        self._db = GraderDatabase(self._config.db_path)
        self._db.initialize()
        self._personal_plot: figure | None = None
        self._consensus_plot: figure | None = None
        self._geometry: GridGeometry | None = None
        self._user_select = pn.widgets.Select(
            name="Reviewer",
            options=self._reviewer_names,
            value=self._reviewer_names[0],
            sizing_mode="stretch_width",
        )
        self._register_button = pn.widgets.Button(
            name="Sign in",
            button_type="primary",
            sizing_mode="stretch_width",
        )
        self._register_button.on_click(self._on_register)
        self._refresh_catalog_button = pn.widgets.Button(
            name="Refresh catalog",
            button_type="default",
            sizing_mode="stretch_width",
        )
        self._refresh_catalog_button.on_click(self._on_refresh_catalog)
        self._status = pn.pane.Markdown("")
        self._hint = pn.pane.Markdown(
            "**Grading:** click a grid cell to cycle "
            "_unset → pass → fail → retry → unset_.\n\n"
            "**Refresh catalog:** re-scan the manifest or data tree; "
            "adds new cells only (keeps existing grades)."
        )
        self._summary_pane = pn.pane.Bokeh(
            figure(),
            sizing_mode="stretch_width",
            styles={"min-height": "640px"},
        )
        self._personal_pane = pn.pane.Bokeh(figure(), sizing_mode="stretch_width")
        self._consensus_pane = pn.pane.Bokeh(figure(), sizing_mode="stretch_width")
        self._catalog, _ = self._sync_catalog()
        days = self._db.list_days()
        if days:
            self.param.day.objects = days
            self.day = days[0]
        self.param.watch(self._on_day_change, "day")
        if pn.state.curdoc is not None:
            pn.state.add_periodic_callback(self._refresh_consensus, period=5000)

    def _sync_catalog(self) -> tuple[pd.DataFrame, int]:
        catalog = discover_catalog(self._config)
        count = self._db.sync_datasets(catalog)
        logger.info("Synced %s dataset rows from discovery", count)
        self._catalog = catalog
        self._update_summary_plot()
        return catalog, count

    def _update_summary_plot(self) -> None:
        self._summary_pane.object = build_catalog_summary_plot(
            self._catalog,
            title="Catalog summary (datasets per day × LST)",
            height=640,
        )

    def _on_register(self, _event=None) -> None:
        try:
            name = ensure_allowed_user(self._user_select.value, self._reviewer_names)
            user = self._db.register_user(name)
        except (ValueError, FileNotFoundError) as exc:
            self._status.object = f"**Error:** {exc}"
            return
        _set_session_user(user)
        self._status.object = f"Signed in as **{user.name}**."
        self._rebuild_view()

    def _on_refresh_catalog(self, _event=None) -> None:
        catalog, count = self._sync_catalog()
        days = self._db.list_days()
        self.param.day.objects = days
        if days and self.day not in days:
            self.day = days[0]
        elif not days:
            self.day = None
        self._rebuild_view()
        self._status.object = (
            f"Catalog refreshed: {len(catalog)} row(s) in manifest, "
            f"{count} synced, {len(days)} day(s) available. Existing grades kept."
        )

    def _on_day_change(self, _event=None) -> None:
        self._rebuild_view()

    def _on_cell_tap(self, dataset_id: int) -> None:
        user = _get_session_user()
        if user is None or self.day is None:
            return
        grades = self._db.grades_for_user_day(user.id, self.day)
        current = grades.get(dataset_id)
        new_grade = next_grade(current)
        if new_grade is None:
            self._db.delete_grade(user.id, dataset_id)
        else:
            self._db.upsert_grade(user.id, dataset_id, new_grade)
        if self._geometry is not None:
            indices = self._geometry.indices_for_dataset(dataset_id)
            if indices is not None:
                lst = self._geometry.lst_labels[indices[0]]
                freq = self._geometry.freq_labels[indices[1]]
                label = new_grade if new_grade is not None else "unset"
                self._status.object = f"**{lst} · {freq}:** {label}"
        self._update_personal_plot(user)
        self._update_consensus_plot()

    def _refresh_consensus(self) -> None:
        if self.day is None or self._consensus_plot is None or self._geometry is None:
            return
        grades_df = self._db.all_grades_for_day(self.day)
        by_ds = grades_by_dataset_from_df(grades_df)
        update_consensus_grid_colors(self._consensus_plot, self._geometry, by_ds)

    def _update_personal_plot(self, user: User) -> None:
        if self._personal_plot is None or self._geometry is None or self.day is None:
            return
        grades = self._db.grades_for_user_day(user.id, self.day)
        update_personal_grid_colors(self._personal_plot, self._geometry, grades)

    def _update_consensus_plot(self) -> None:
        if self._consensus_plot is None or self._geometry is None or self.day is None:
            return
        grades_df = self._db.all_grades_for_day(self.day)
        by_ds = grades_by_dataset_from_df(grades_df)
        update_consensus_grid_colors(self._consensus_plot, self._geometry, by_ds)

    def _rebuild_view(self) -> None:
        user = _get_session_user()
        if user is None or self.day is None:
            self._personal_pane.object = figure(width=700, height=200, title="Select a day after registering")
            self._consensus_pane.object = figure(width=700, height=200)
            return
        datasets = self._db.datasets_for_day(self.day)
        if datasets.empty:
            self._personal_pane.object = figure(
                width=700, height=200, title=f"No datasets for {self.day}"
            )
            self._consensus_pane.object = figure(width=700, height=200)
            return
        self._geometry = GridGeometry.from_datasets(datasets)
        grades = self._db.grades_for_user_day(user.id, self.day)
        self._personal_plot = build_personal_grid(
            self._geometry,
            grades,
            on_tap=self._on_cell_tap,
            title=f"Your grades — {self.day}",
        )
        grades_df = self._db.all_grades_for_day(self.day)
        by_ds = grades_by_dataset_from_df(grades_df)
        self._consensus_plot = build_consensus_grid(
            self._geometry,
            by_ds,
            title=f"All reviewers — {self.day}",
        )
        self._personal_pane.object = self._personal_plot
        self._consensus_pane.object = self._consensus_plot

    @property
    def view(self) -> pn.Column:
        user = _get_session_user()
        header = pn.pane.Markdown(
            "## Dataset grader\n"
            "Sign in, pick a day, then grade cells below. "
            "Consensus grid shows all reviewers."
        )
        user_line = (
            pn.pane.Markdown(f"**Signed in:** {user.name}")
            if user
            else pn.pane.Markdown("_Not signed in_")
        )
        day_param = pn.Param(
            self.param.day,
            widgets={"day": pn.widgets.Select},
            show_name=True,
            name="Day",
        )
        controls = pn.Column(
            header,
            self._user_select,
            self._register_button,
            self._refresh_catalog_button,
            user_line,
            day_param,
            self._hint,
            self._status,
            sizing_mode="stretch_width",
            styles={"flex": "1", "min-width": "0"},
        )
        summary_panel = pn.Column(
            pn.pane.Markdown("### Catalog summary"),
            self._summary_pane,
            sizing_mode="stretch_width",
            styles={"flex": "1", "min-width": "0"},
        )
        top_row = pn.Row(
            controls,
            summary_panel,
            sizing_mode="stretch_width",
        )
        main = pn.Column(
            top_row,
            pn.pane.Markdown("### Your grading grid"),
            self._personal_pane,
            pn.pane.Markdown("### Consensus (hover for details)"),
            self._consensus_pane,
            sizing_mode="stretch_width",
        )
        if user is not None:
            self._rebuild_view()
        return main


def create_app() -> pn.Column:
    return DatasetGraderApp().view


app = create_app()
app.servable()
