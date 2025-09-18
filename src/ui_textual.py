"""Textual-based dashboard for the project (experimental).

This module provides a Textual app that mirrors the Rich dashboard layout:
header, left menu, right prompt+output, and footer. It integrates with the
existing pipeline logic in ``setup_project.py`` via a small context object so
that business logic remains unchanged.

Docstrings use NumPy style and English.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

# Textual imports are local to this module to keep dependency surface minimal
if TYPE_CHECKING:
    from textual.app import App, ComposeResult
else:
    App = object
    ComposeResult = Any
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Input, Label, ListItem, ListView, Static


@dataclass
class DashboardContext:
    """Wiring for the Textual app to call into project logic.

    Attributes
    ----------
    t : Callable[[str], str]
        Translation function mapping keys to localized strings.
    get_program_descriptions : Callable[[], dict[str, tuple[str, str]]]
        Returns program descriptions per program id.
    run_ai_check : Callable[[], tuple[bool, str]]
        Silent AI connectivity check returning ``(ok, detail)``.
    run_program : Callable[[str, Path, bool], bool]
        Execute a program step; signature mirrors ``setup_project.run_program``.
    render_pipeline_table : Callable[[str, str, str], Any]
        Returns a Rich renderable representing the status table.
    log_dir : Path
        Path to the project's log directory.
    program1_path : Path
        Path to Program 1 script.
    program2_path : Path
        Path to Program 2 script.
    program3_path : Path
        Path to Program 3 script.
    set_tui_mode : Callable[[Callable[[Any], None] | None, Callable[[Any], None] | None], Callable[[], None]]
        Adapter hook to enable/disable TUI updates inside ``setup_project``.
    lang : Callable[[], str]
        Returns current language label ("en"/"sv").
    venv_dir : Callable[[], Path]
        Returns venv folder path.
    """

    t: Callable[[str], str]
    get_program_descriptions: Callable[[], dict[str, tuple[str, str]]]
    run_ai_check: Callable[[], tuple[bool, str]]
    run_program: Callable[..., bool]
    render_pipeline_table: Callable[[str, str, str], Any]
    log_dir: Path
    program1_path: Path
    program2_path: Path
    program3_path: Path
    set_tui_mode: Callable[
        [Callable[[Any], None] | None, Callable[[Any], None] | None], Callable[[], None]
    ]
    lang: Callable[[], str]
    venv_dir: Callable[[], Path]


class SetupDashboardApp(App):
    """Textual application implementing the dashboard UI.

    Notes
    -----
    - The right pane is split into a prompt area (small, top) and an output area (larger, bottom).
    - All input occurs in the prompt area via a single-line ``Input`` widget.
    - Pipeline progress for Program 2 is streamed via the existing ``run_program``
      logic by enabling the TUI adapter provided by :func:`set_tui_mode`.
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
    ]

    CSS: ClassVar[str] = """
    #root {
        height: 100%;
    }
    #header {
        background: $accent;
        color: black;
        padding: 1 2;
    }
    #footer {
        dock: bottom;
    }
    #menu { width: 36; border: round $accent; }
    #content { border: round $accent; }
    #prompt { height: 3; border-bottom: solid $accent; }
    #output { height: 1fr; }
    .pad { padding: 1 1; }
    """

    def __init__(self, ctx: DashboardContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.active_view: reactive[str] = reactive("menu")
        self.prompt_input: Input | None = None
        self.prompt_label: Static | None = None
        self.output: Static | None = None
        self._restore_tui: Callable[[], None] | None = None

    def compose(self) -> ComposeResult:
        """Compose the UI layout for the Textual app.

        Returns
        -------
        ComposeResult
            The composed child widgets.
        """
        header = Static("Skoltexter by AI — Setup", id="header")
        # Left menu
        menu = ListView(
            ListItem(Label("1. " + self.ctx.t("menu_option_1")[3:])),
            ListItem(Label("2. " + self.ctx.t("menu_option_2")[3:])),
            ListItem(Label("3. " + self.ctx.t("menu_option_3")[3:])),
            ListItem(Label("4. " + self.ctx.t("menu_option_4")[3:])),
            ListItem(Label("5. " + self.ctx.t("menu_option_5")[3:])),
            ListItem(Label("6. " + self.ctx.t("menu_option_6")[3:])),
            id="menu",
        )
        # Right content
        self.prompt_label = Static("", id="prompt")
        self.prompt_input = Input(placeholder=">")
        prompt_box = Horizontal(self.prompt_label, self.prompt_input, id="prompt")
        self.output = Static("", id="output")
        right = Vertical(prompt_box, self.output, id="content")
        body = Horizontal(menu, right)
        # Footer
        footer = Footer(id="footer")
        yield Vertical(header, body, footer, id="root")

    def on_mount(self) -> None:
        """Initialize screen state on mount."""
        self._update_footer()
        self._show_menu_message()
        if self.prompt_input:
            self.set_focus(self.prompt_input)

    def _update_footer(self) -> None:
        lang_label = "Svenska" if self.ctx.lang() == "sv" else "English"
        venv_status = (
            str(self.ctx.venv_dir().resolve())
            if self.ctx.venv_dir().exists()
            else "<not created>"
        )
        text = f"Language: {lang_label} | Venv: {venv_status}"
        # Footer widget itself provides key hints; render status in output header
        if self.output:
            self.output.update(Static(""))
        if self.prompt_label:
            self.prompt_label.update(text)

    def _show_menu_message(self) -> None:
        if not self.output:
            return
        msg = (
            "Välj ett menyval till vänster.\n"
            "- Programbeskrivningar (2)\n- Pipeline (3)\n- Loggar (4)\n- Avsluta (6)"
        )
        self.output.update(Static(msg, classes="pad"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """React to left menu selection and switch right pane view."""
        label = (
            event.item.query_one(Label).renderable
            if isinstance(event.item, ListItem)
            else ""
        )
        text = str(label)
        if text.startswith("1."):
            self.active_view = "env"
            self._render_env_unsupported()
        elif text.startswith("2."):
            self.active_view = "descriptions"
            self._render_descriptions_home()
        elif text.startswith("3."):
            self.active_view = "pipeline"
            self._render_pipeline_home()
        elif text.startswith("4."):
            self.active_view = "logs"
            self._render_logs_home()
        elif text.startswith("5."):
            self.active_view = "reset"
            self._render_reset_info()
        elif text.startswith("6."):
            self.exit()

    def _render_env_unsupported(self) -> None:
        if self.prompt_label:
            self.prompt_label.update(
                "Environment setup via Textual is not interactive yet."
            )
        if self.output:
            self.output.update(
                Static("Använd CLI-läget för venv & dependencies.", classes="pad")
            )

    def _render_reset_info(self) -> None:
        if self.prompt_label:
            self.prompt_label.update("Återställning görs via CLI i detta läge.")
        if self.output:
            self.output.update(
                Static("Kör '5' i Rich/CLI-menyn för full reset.", classes="pad")
            )

    # --- Program Descriptions View ---
    def _render_descriptions_home(self) -> None:
        if not self.output:
            return
        rows = self.ctx.get_program_descriptions()
        lines = [f"{k}. {v[0]}" for k, v in rows.items()] + ["0. Tillbaka"]
        content = "\n".join(lines)
        self.output.update(Static(content, classes="pad"))
        if self.prompt_label:
            self.prompt_label.update(self.ctx.t("select_program_to_describe"))
        if self.prompt_input:
            self.prompt_input.value = ""

    def action_quit(self) -> None:
        """Exit the app."""
        self.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Process input from the prompt line based on active view."""
        value = (event.value or "").strip()
        if self.active_view == "descriptions":
            self._handle_desc_input(value)
        elif self.active_view == "logs":
            self._handle_logs_input(value)
        elif self.active_view == "pipeline":
            self._handle_pipeline_input(value)
        else:
            # No-op for other views
            if self.prompt_input:
                self.prompt_input.value = ""

    def _handle_desc_input(self, value: str) -> None:
        if value == "0":
            self._show_menu_message()
            self.active_view = "menu"
            if self.prompt_label:
                self.prompt_label.update("")
            if self.prompt_input:
                self.prompt_input.value = ""
            return
        rows = self.ctx.get_program_descriptions()
        if value in rows:
            short, long = rows[value]
            # Render Markdown as plain text inside Textual using Static
            from rich.markdown import Markdown

            if self.output:
                self.output.update(Markdown(long))
        else:
            if self.output:
                self.output.update(Static(self.ctx.t("invalid_choice")))
        if self.prompt_input:
            self.prompt_input.value = ""

    # --- Logs View ---
    def _render_logs_home(self) -> None:
        files = [
            p
            for p in self.ctx.log_dir.iterdir()
            if p.is_file() and p.name.endswith(".log")
        ]
        files.sort()
        if not files:
            if self.output:
                self.output.update(Static(self.ctx.t("no_logs")))
            if self.prompt_label:
                self.prompt_label.update("")
            return
        listing = [f"{i}. {p.name}" for i, p in enumerate(files, 1)] + ["0. Tillbaka"]
        if self.output:
            self.output.update(Static("\n".join(listing), classes="pad"))
        if self.prompt_label:
            self.prompt_label.update(self.ctx.t("select_log_prompt"))
        if self.prompt_input:
            self.prompt_input.value = ""

    def _handle_logs_input(self, value: str) -> None:
        files = [
            p
            for p in self.ctx.log_dir.iterdir()
            if p.is_file() and p.name.endswith(".log")
        ]
        files.sort()
        if value == "0":
            self._show_menu_message()
            self.active_view = "menu"
            return
        selected: Path | None = None
        if value.isdigit():
            idx = int(value) - 1
            if 0 <= idx < len(files):
                selected = files[idx]
        if not selected:
            selected = next(
                (p for p in files if p.name == value or p.name.startswith(value)), None
            )
        if selected and selected.exists():
            from rich.syntax import Syntax

            text = selected.read_text(encoding="utf-8")
            if self.output:
                self.output.update(Syntax(text, "text"))
        else:
            if self.output:
                self.output.update(Static(self.ctx.t("invalid_choice")))
        if self.prompt_input:
            self.prompt_input.value = ""

    # --- Pipeline View ---
    def _render_pipeline_home(self) -> None:
        if self.output:
            table = self.ctx.render_pipeline_table(
                "⏳ Väntar", "⏳ Väntar", "⏳ Väntar"
            )
            self.output.update(table)
        if self.prompt_label:
            self.prompt_label.update(
                "Skriv 'run' för att starta (eller 'back' för meny)"
            )
        if self.prompt_input:
            self.prompt_input.value = ""

    def _handle_pipeline_input(self, value: str) -> None:
        if value.lower() in {"back", "0"}:
            self._show_menu_message()
            self.active_view = "menu"
            return
        # default: run pipeline
        self._start_pipeline_thread()
        if self.prompt_input:
            self.prompt_input.value = ""

    def _start_pipeline_thread(self) -> None:
        # Enable TUI mode so run_program can stream progress updates in-place
        def update_right(renderable: Any) -> None:
            if self.output:
                # Updates must occur on the UI thread
                self.call_from_thread(self.output.update, renderable)

        def update_prompt(renderable: Any) -> None:
            if self.prompt_label:
                self.call_from_thread(self.prompt_label.update, renderable)

        self._restore_tui = self.ctx.set_tui_mode(update_right, update_prompt)
        self.run_worker(self._pipeline_worker, exclusive=True)

    async def _pipeline_worker(self) -> None:
        # Build and update status table as the pipeline progresses
        def set_status(s1: str, s2: str, s3: str) -> None:
            table = self.ctx.render_pipeline_table(s1, s2, s3)
            if self.output:
                self.call_from_thread(self.output.update, table)

        # Optional AI connectivity check
        ok, detail = self.ctx.run_ai_check()
        if not ok:
            from rich.panel import Panel

            if self.output:
                self.call_from_thread(
                    self.output.update,
                    Panel(f"AI check failed: {detail}", border_style="red", title="AI"),
                )
            if self._restore_tui:
                self._restore_tui()
            return

        # Program 1
        s1, s2, s3 = "▶️ Körs", "⏳ Väntar", "⏳ Väntar"
        set_status(s1, s2, s3)
        ok1 = self.ctx.run_program(
            "program_1", self.ctx.program1_path, stream_output=False
        )
        s1 = "✅ Klart" if ok1 else "❌ Misslyckades"
        set_status(s1, s2, s3)
        # Program 2
        s2 = "▶️ Körs"
        set_status(s1, s2, s3)
        ok2 = self.ctx.run_program(
            "program_2", self.ctx.program2_path, stream_output=True
        )
        s2 = "✅ Klart" if ok2 else "❌ Misslyckades"
        set_status(s1, s2, s3)
        # Program 3
        s3 = "▶️ Körs"
        set_status(s1, s2, s3)
        ok3 = self.ctx.run_program(
            "program_3", self.ctx.program3_path, stream_output=False
        )
        s3 = "✅ Klart" if ok3 else "❌ Misslyckades"
        set_status(s1, s2, s3)

        if self._restore_tui:
            self._restore_tui()
