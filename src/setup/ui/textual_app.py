"""Textual-based dashboard for the project (moved into ui package).

This module is a direct move of the previous `src/ui_textual.py` file into
the `src.setup.ui` package and updated to invoke pipeline functions
directly via the provided :class:`DashboardContext` contract.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

# Textual imports are local to this module to keep dependency surface minimal.
# During type-checking we import real types; at runtime we fall back to
# runtime-safe placeholders to avoid hard dependency on textual.
if TYPE_CHECKING:
    # Define a lightweight protocol that expresses the minimal App API
    # used by this module. Using a Protocol allows static type checkers
    # to reason about calls such as `set_focus`, `exit` and
    # `call_from_thread` without importing the optional `textual` package.
    from collections.abc import Callable

    class _AppBase:
        """A lightweight, typed base class used only for static checking.

        The methods provide simple concrete stubs so subclasses are not
        considered abstract by static type checkers.
        """

        def set_focus(self, widget: Any) -> None:  # pragma: no cover - typing only
            """Set focus to the given widget."""
            return None

        def exit(self) -> None:  # pragma: no cover - typing only
            """Exit the application."""
            return None

        def call_from_thread(
            self, func: Callable[..., Any], *args: Any, **kwargs: Any
        ) -> Any:  # pragma: no cover - typing only
            """Call a function from a non-UI thread on the UI thread."""
            return None

        def run_worker(
            self, coro: Callable[..., Any], exclusive: bool = False
        ) -> None:  # pragma: no cover - typing only
            """Schedule and run a background coroutine within the UI runtime."""
            return None

        def run(
            self, *args: Any, **kwargs: Any
        ) -> Any:  # pragma: no cover - typing only
            """Start the application's event loop."""
            return None

    AppType = _AppBase
    ComposeResult = Any
else:
    AppType = object
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
    run_program : Callable[[str], bool]
        Execute a program step by name. The callable should accept the
        program name (``"program_1"``, ``"program_2"``, ``"program_3"``)
        and an optional ``stream_output`` kwarg. It must return ``True`` on
        success and ``False`` on failure.
    render_pipeline_table : Callable[[str, str, str], Any]
        Returns a Rich renderable representing the status table.
    log_dir : Path
        Path to the project's log directory.
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
    set_tui_mode: Callable[
        [Callable[[Any], None] | None, Callable[[Any], None] | None], Callable[[], None]
    ]
    lang: Callable[[], str]
    venv_dir: Callable[[], Path]


class SetupDashboardApp(AppType):
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
        """Initialise the Textual dashboard application.

        Parameters
        ----------
        ctx : DashboardContext
            Wiring object that provides translation, program runners and
            rendering helpers used by the UI.
        """
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
        """Update footer information such as language and venv status.

        This refreshes the small status line shown above the input prompt so
        users can quickly see which language and venv are active.
        """
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
        """Display the default menu guidance in the main output area.

        This helper writes a short, localized instruction string to the
        output widget instructing the user how to navigate the menu.
        """
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
        """Render a short message indicating environment setup is not supported.

        The Textual UI currently does not implement interactive environment
        creation; this helper notifies the user and suggests the CLI path.
        """
        if self.prompt_label:
            self.prompt_label.update(
                "Environment setup via Textual is not interactive yet."
            )
        if self.output:
            self.output.update(
                Static("Använd CLI-läget för venv & dependencies.", classes="pad")
            )

    def _render_reset_info(self) -> None:
        """Inform the user that resets are performed via the CLI menu.

        This is a lightweight informational view that points to the CLI for
        destructive reset operations.
        """
        if self.prompt_label:
            self.prompt_label.update("Återställning görs via CLI i detta läge.")
        if self.output:
            self.output.update(
                Static("Kör '5' i Rich/CLI-menyn för full reset.", classes="pad")
            )

    # --- Program Descriptions View ---
    def _render_descriptions_home(self) -> None:
        """Show a brief list of available program descriptions.

        The content is rendered as a simple list with a numeric selection.
        """
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
        """Handle input from the descriptions view and render selected text.

        Parameters
        ----------
        value : str
            The user's input string; numeric or name-based selection is
            supported.
        """
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
            _short, long = rows[value]
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
        """Render the logs view with selectable log filenames.

        The view lists available .log files and prompts the user to select
        one for viewing.
        """
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
        """Handle user selection in the logs view and display file contents.

        Parameters
        ----------
        value : str
            User input corresponding to a file index or filename prefix.
        """
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
        """Render the pipeline overview table and prepare the prompt.

        Shows a table summarising the three pipeline steps and instructs the
        user how to start execution.
        """
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
        """Handle pipeline commands from the prompt (start/back).

        Parameters
        ----------
        value : str
            The input string from the prompt area.
        """
        if value.lower() in {"back", "0"}:
            self._show_menu_message()
            self.active_view = "menu"
            return
        # default: run pipeline
        self._start_pipeline_thread()
        if self.prompt_input:
            self.prompt_input.value = ""

    def _start_pipeline_thread(self) -> None:
        """Prepare and start the background worker that runs the pipeline.

        This method registers TUI update callbacks with the provided
        DashboardContext and starts an exclusive worker coroutine to avoid
        concurrent pipeline runs.
        """

        # Enable TUI mode so run_program can stream progress updates in-place
        def update_right(renderable: Any) -> None:
            """Update the right-hand content area from worker threads.

            The call is marshalled to the UI thread using ``call_from_thread``.
            """
            if self.output:
                # Updates must occur on the UI thread
                self.call_from_thread(self.output.update, renderable)

        def update_prompt(renderable: Any) -> None:
            """Update the small prompt label area from worker threads."""
            if self.prompt_label:
                self.call_from_thread(self.prompt_label.update, renderable)

        self._restore_tui = self.ctx.set_tui_mode(update_right, update_prompt)
        self.run_worker(self._pipeline_worker, exclusive=True)

    async def _pipeline_worker(self) -> None:
        """Background worker coroutine that runs the three pipeline steps.

        The worker updates the UI status table as each program step begins and
        completes. If the optional AI connectivity check fails, the worker
        displays an error and restores the previous TUI state.
        """

        # Build and update status table as the pipeline progresses
        def set_status(s1: str, s2: str, s3: str) -> None:
            """Update the pipeline status table on the UI thread."""
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
        ok1 = self.ctx.run_program("program_1", stream_output=False)
        s1 = "✅ Klart" if ok1 else "❌ Misslyckades"
        set_status(s1, s2, s3)
        # Program 2
        s2 = "▶️ Körs"
        set_status(s1, s2, s3)
        ok2 = self.ctx.run_program("program_2", stream_output=True)
        s2 = "✅ Klart" if ok2 else "❌ Misslyckades"
        set_status(s1, s2, s3)
        # Program 3
        s3 = "▶️ Körs"
        set_status(s1, s2, s3)
        ok3 = self.ctx.run_program("program_3", stream_output=False)
        s3 = "✅ Klart" if ok3 else "❌ Misslyckades"
        set_status(s1, s2, s3)

        if self._restore_tui:
            self._restore_tui()
