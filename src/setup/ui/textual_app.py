"""Textual-based dashboard for the project (moved into ui package).

This is the same Textual app previously at `src/ui_textual.py`, moved
under the `src.setup.ui` package so all UI code is colocated.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

# Textual imports are local to this module to keep dependency surface minimal
if TYPE_CHECKING:
    from textual.app import App, ComposeResult
else:  # pragma: no cover - runtime fallback when textual is not installed
    App = object
    ComposeResult = Any
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Input, Label, ListItem, ListView, Static


@dataclass
class DashboardContext:
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
    """Textual dashboard application for the setup TUI.

    This application composes a left-hand menu and a right-hand content
    area consisting of a prompt and output region. It is a thin UI layer
    that delegates business logic to the supplied :class:`DashboardContext`.
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("q", "quit", "Quit")]

    CSS: ClassVar[str] = """
    #root { height: 100%; }
    #header { background: $accent; color: black; padding: 1 2; }
    #footer { dock: bottom; }
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
        """Compose the UI layout and yield the root container.

        Returns
        -------
        ComposeResult
            The composed widgets for Textual to render.
        """
        header = Static("Skoltexter by AI — Setup", id="header")
        menu = ListView(
            ListItem(Label("1. " + self.ctx.t("menu_option_1")[3:])),
            ListItem(Label("2. " + self.ctx.t("menu_option_2")[3:])),
            ListItem(Label("3. " + self.ctx.t("menu_option_3")[3:])),
            ListItem(Label("4. " + self.ctx.t("menu_option_4")[3:])),
            ListItem(Label("5. " + self.ctx.t("menu_option_5")[3:])),
            ListItem(Label("6. " + self.ctx.t("menu_option_6")[3:])),
            id="menu",
        )
        self.prompt_label = Static("", id="prompt")
        self.prompt_input = Input(placeholder=">")
        prompt_box = Horizontal(self.prompt_label, self.prompt_input, id="prompt")
        self.output = Static("", id="output")
        right = Vertical(prompt_box, self.output, id="content")
        body = Horizontal(menu, right)
        footer = Footer(id="footer")
        yield Vertical(header, body, footer, id="root")

    def on_mount(self) -> None:
        """Initialize the UI when the application mounts.

        This sets up the footer and displays the initial menu message.
        """
        self._update_footer()
        self._show_menu_message()
        if self.prompt_input:
            self.set_focus(self.prompt_input)

    def _update_footer(self) -> None:
        """Update the footer and prompt label with current status info."""
        lang_label = "Svenska" if self.ctx.lang() == "sv" else "English"
        venv_status = (
            str(self.ctx.venv_dir().resolve())
            if self.ctx.venv_dir().exists()
            else "<not created>"
        )
        text = f"Language: {lang_label} | Venv: {venv_status}"
        if self.output:
            self.output.update(Static(""))
        if self.prompt_label:
            self.prompt_label.update(text)

    def _show_menu_message(self) -> None:
        """Display the initial menu help text in the output area."""
        if not self.output:
            return
        msg = (
            "Välj ett menyval till vänster.\n"
            "- Programbeskrivningar (2)\n- Pipeline (3)\n- Loggar (4)\n- Avsluta (6)"
        )
        self.output.update(Static(msg, classes="pad"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection in the left-hand menu and switch views."""
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
        """Render a short message that Textual-based env setup is not supported."""
        if self.prompt_label:
            self.prompt_label.update(
                "Environment setup via Textual is not interactive yet."
            )
        if self.output:
            self.output.update(
                Static("Använd CLI-läget för venv & dependencies.", classes="pad")
            )

    def _render_reset_info(self) -> None:
        """Render reset instructions for the reset view."""
        if self.prompt_label:
            self.prompt_label.update("Återställning görs via CLI i detta läge.")
        if self.output:
            self.output.update(
                Static("Kör '5' i Rich/CLI-menyn för full reset.", classes="pad")
            )

    def _render_descriptions_home(self) -> None:
        """Render the program descriptions view in the output pane."""
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
        """Quit the application cleanly."""
        self.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle a submitted input value from the prompt line."""
        value = (event.value or "").strip()
        if self.active_view == "descriptions":
            self._handle_desc_input(value)
        elif self.active_view == "logs":
            self._handle_logs_input(value)
        elif self.active_view == "pipeline":
            self._handle_pipeline_input(value)
