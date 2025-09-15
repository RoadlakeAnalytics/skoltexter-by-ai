"""Program descriptions and log viewing UI helpers for the ui package.

Extracted into a shim-free module under the UI package.
"""

from __future__ import annotations

from src.config import LOG_DIR
from src.setup.console_helpers import (
    Markdown,
    Panel,
    Syntax,
    Table,
    rprint,
    ui_has_rich,
)
from src.setup.i18n import translate
from src.setup.ui.basic import ui_menu, ui_rule
from src.setup.ui.prompts import ask_text


def get_program_descriptions() -> dict[str, tuple[str, str]]:
    return {
        "1": (translate("program_1_desc_short"), translate("program_1_desc_long")),
        "2": (translate("program_2_desc_short"), translate("program_2_desc_long")),
        "3": (translate("program_3_desc_short"), translate("program_3_desc_long")),
    }


def view_program_descriptions() -> None:
    ui_rule(translate("program_descriptions_title"))
    while True:
        descriptions = get_program_descriptions()
        items = [(k, v[0]) for k, v in descriptions.items()]
        items.append(("0", translate("return_to_menu")))
        ui_menu(items)
        choice = ask_text(translate("select_program_to_describe"))
        if choice == "0":
            break
        if choice in descriptions:
            title, body = descriptions[choice]
            if ui_has_rich():
                rprint(Markdown(body))
            else:
                rprint(body)
        else:
            rprint(translate("invalid_choice"))


def _view_program_descriptions_tui(
    update_right: callable, update_prompt: callable
) -> None:
    descriptions = get_program_descriptions()
    items = [(k, v[0]) for k, v in descriptions.items()]
    items.append(("0", translate("return_to_menu")))
    t = Table(show_header=True, header_style="bold blue")
    t.add_column("#")
    t.add_column("Val")
    for k, label in items:
        t.add_row(k, label)
    update_right(t)
    choice = ask_text(translate("select_program_to_describe"))
    if choice == "0":
        return
    if choice in descriptions:
        title, body = descriptions[choice]
        update_right(Panel(Markdown(body), title=title))
    else:
        update_right(
            Panel(translate("invalid_choice"), title="Info", border_style="yellow")
        )


def _view_logs_tui(update_right: callable, update_prompt: callable) -> None:
    if not LOG_DIR.exists() or not any(LOG_DIR.iterdir()):
        update_right(Panel(translate("no_logs"), title="Logs"))
        return
    log_files = sorted(
        [p for p in LOG_DIR.iterdir() if p.is_file() and p.name.endswith(".log")]
    )
    if not log_files:
        update_right(Panel(translate("no_logs"), title="Logs"))
        return
    while True:
        tbl = Table(show_header=True, header_style="bold blue")
        tbl.add_column("#")
        tbl.add_column("Log")
        for i, p in enumerate(log_files, 1):
            tbl.add_row(str(i), p.name)
        tbl.add_row("0", translate("return_to_menu"))
        update_right(Panel(tbl, title="Logs"))
        choice = ask_text(translate("select_log_prompt"))
        if choice == "0":
            break
        selected = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(log_files):
                selected = log_files[idx]
        if not selected:
            selected = next(
                (p for p in log_files if p.name == choice or p.name.startswith(choice)),
                None,
            )
        if selected and selected.exists():
            txt = selected.read_text(encoding="utf-8")
            update_right(
                Panel(Syntax(txt, "text", theme="monokai"), title=selected.name)
            )
        else:
            update_right(
                Panel(translate("invalid_choice"), title="Info", border_style="yellow")
            )


def view_logs() -> None:
    ui_rule(translate("logs_title"))
    if not LOG_DIR.exists() or not any(LOG_DIR.iterdir()):
        rprint(translate("no_logs"))
        return
    log_files = sorted(
        [p for p in LOG_DIR.iterdir() if p.is_file() and p.name.endswith(".log")]
    )
    if not log_files:
        rprint(translate("no_logs"))
        return
    while True:
        ui_rule(translate("logs_title"))
        ui_menu(
            [(str(i), p.name) for i, p in enumerate(log_files, start=1)]
            + [("0", translate("return_to_menu"))]
        )
        try:
            choice = ask_text(translate("select_log_prompt"))
            if choice == "0":
                break
            selected_log = None
            if choice.isdigit():
                log_index = int(choice) - 1
                if 0 <= log_index < len(log_files):
                    selected_log = log_files[log_index]
            if not selected_log:
                selected_log = next(
                    (
                        file_path
                        for file_path in log_files
                        if file_path.name == choice or file_path.name.startswith(choice)
                    ),
                    None,
                )
            if selected_log:
                rprint(f"\n--- {translate('viewing_log')}{selected_log.name} ---")
                content = selected_log.read_text(encoding="utf-8")
                if ui_has_rich():
                    rprint(Syntax(content, "text", theme="monokai", line_numbers=False))
                else:
                    rprint(content)
                rprint(f"--- End of {selected_log.name} ---\n")
            else:
                rprint(translate("invalid_choice"))
        except Exception as error:
            # Log errors quietly during tests
            rprint(f"Error reading log file: {error}")


__all__ = [
    "get_program_descriptions",
    "view_program_descriptions",
    "_view_program_descriptions_tui",
    "_view_logs_tui",
    "view_logs",
]
