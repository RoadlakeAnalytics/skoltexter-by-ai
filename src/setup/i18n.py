"""Internationalization for the setup UI and pipeline.

Centralizes user-facing texts and language selection. Maintains ``LANG``.
"""

from src.config import LOG_DIR, VENV_DIR

LANG: str = "en"

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "Welcome to the School Data Processing Project Setup!",
        "language_prompt": "Select language (1 for English, 2 for Svenska): ",
        "invalid_choice": "Invalid choice. Please try again.",
        "venv_active": "A virtual environment is already active: ",
        "venv_exists": f"Virtual environment '{VENV_DIR.name}' already exists.",
        "venv_menu_title": "\n--- Virtual Environment Setup ---",
        "venv_menu_option_1": "1. Create a virtual environment and install dependencies",
        "venv_menu_option_2": "2. Continue without a virtual environment",
        "venv_menu_prompt": "Choose an option (1 or 2): ",
        "venv_menu_info": "",
        "create_venv_prompt": "Create/recreate and install dependencies? (y/n, default y): ",
        "activate_venv_prompt": f"Virtual environment '{VENV_DIR.name}' exists. Install/update dependencies? (y/n, default y): ",
        "no_venv_prompt": f"No virtual environment found. Create '{VENV_DIR.name}' and install dependencies? (y/n, default y): ",
        "creating_venv": "Creating virtual environment...",
        "installing_deps": "Installing dependencies...",
        "deps_installed": "Dependencies installed.",
        "deps_install_failed": "Failed to install dependencies.",
        "venv_ready": "Virtual environment is set up.",
        "venv_skipped": "Virtual environment setup skipped.",
        "main_menu_title": "\n--- Main Menu ---",
        "menu_option_1": "1. Manage Virtual Environment & Dependencies",
        "menu_option_2": "2. View Program Descriptions",
        "menu_option_3": "3. Run Processing Pipeline",
        "menu_option_4": "4. View Logs",
        "menu_option_5": "5. Reset Project",
        "menu_option_6": "6. Exit",
        "enter_choice": "Enter your choice: ",
        "program_descriptions_title": "\n--- Program Descriptions ---",
        "program_1_desc_short": "Program 1 (Generate Markdowns from CSV)",
        "program_1_desc_long": (
            "Reads school data from the main CSV file and uses a template to generate "
            "individual markdown files for each school."
        ),
        "program_2_desc_short": "Program 2 (AI Processor for School Descriptions)",
        "program_2_desc_long": (
            "Takes the markdown files from Program 1 and sends their content to an "
            "AI service. The AI generates more detailed school descriptions."
        ),
        "program_3_desc_short": "Program 3 (Generate Website)",
        "program_3_desc_long": (
            "Loads school names from the CSV and their AI-generated descriptions "
            "and generates a standalone HTML file."
        ),
        "select_program_to_describe": "Select program to describe (1, 2, 3, or 0 to return): ",
        "pipeline_title": "\n--- Run Processing Pipeline ---",
        "run_program_1_prompt": "Run Program 1? (y/n/s, default y): ",
        "running_program_1": "Running Program 1...",
        "program_1_complete": "Program 1 completed.",
        "program_1_failed": "Program 1 failed or was skipped.",
        "run_program_2_prompt": "Run Program 2? (y/n/s, default y): ",
        "running_program_2": "Running Program 2...",
        "program_2_complete": "Program 2 completed.",
        "program_2_failed": "Program 2 failed or was skipped.",
        "program_2_skipped": "Program 2 skipped.",
        "run_program_3_prompt": "Run Program 3? (y/n/s, default y): ",
        "running_program_3": "Running Program 3...",
        "program_3_complete": "Program 3 completed.",
        "program_3_failed": "Program 3 failed or was skipped.",
        "pipeline_complete": "Processing pipeline finished.",
        "ai_check_title": "\n--- AI Connectivity Check ---",
        "ai_check_prompt": "Run a quick AI connectivity test? (y/n, default y): ",
        "ai_check_running": "Testing AI connectivity...",
        "ai_check_ok": "AI connectivity OK. Received expected reply.",
        "ai_check_fail": "AI connectivity failed. Please verify your .env, network, and Azure settings.",
        "logs_title": "\n--- View Logs ---",
        "no_logs": f"No log files found in {LOG_DIR}",
        "select_log_prompt": "Enter the log file name to view (or 0 to return): ",
        "viewing_log": "Viewing log: ",
        "log_not_found": "Log file not found.",
        "exiting": "Exiting setup script.",
        "confirm_recreate_venv": f"WARNING: '{VENV_DIR.name}' exists. Recreate? (y/n, default n): ",
        "return_to_menu": "Return to Main Menu",
        "reset_option": "6. Reset Project",
        "reset_confirm": "Delete ALL generated files? (y/n, default n): ",
        "reset_complete": "Project reset completed.",
        "reset_cancelled": "Reset cancelled.",
        "azure_env_intro": "The following Azure OpenAI values are required for local storage so the program can call Azure OpenAI.",
        "azure_env_storage": "They will be stored in the .env file. These values are only needed for local storage and are not shared.",
        "azure_env_prompt": "Enter value for {key}: ",
        "quality_suite_ok": "All local quality checks passed.",
        "quality_suite_fail": "One or more local quality checks failed.",
    },
    "sv": {
        "welcome": "Välkommen till School Data Processing-projektets setup!",
        "language_prompt": "Välj språk (1 för English, 2 för Svenska): ",
        "invalid_choice": "Ogiltigt val. Försök igen.",
        "venv_active": "En virtuell miljö är redan aktiv: ",
        "venv_exists": f"Virtuell miljö '{VENV_DIR.name}' finns redan.",
        "venv_menu_title": "\n--- Virtuell miljö ---",
        "venv_menu_option_1": "1. Skapa virtuell miljö och installera beroenden",
        "venv_menu_option_2": "2. Fortsätt utan virtuell miljö",
        "venv_menu_prompt": "Välj ett alternativ (1 eller 2): ",
        "venv_menu_info": "",
        "create_venv_prompt": "Skapa/återskapa och installera beroenden? (y/n, standard y): ",
        "activate_venv_prompt": f"Virtuell miljö '{VENV_DIR.name}' finns. Installera/uppdatera beroenden? (y/n, standard y): ",
        "no_venv_prompt": f"Ingen virtuell miljö hittades. Skapa '{VENV_DIR.name}' och installera beroenden? (y/n, standard y): ",
        "creating_venv": "Skapar virtuell miljö...",
        "installing_deps": "Installerar beroenden...",
        "deps_installed": "Beroenden installerade.",
        "deps_install_failed": "Misslyckades att installera beroenden.",
        "venv_ready": "Virtuell miljö klar.",
        "venv_skipped": "Steget för virtuell miljö hoppades över.",
        "main_menu_title": "\n--- Huvudmeny ---",
        "menu_option_1": "1. Hantera virtuell miljö & beroenden",
        "menu_option_2": "2. Visa programbeskrivningar",
        "menu_option_3": "3. Kör bearbetningsflöde",
        "menu_option_4": "4. Visa loggar",
        "menu_option_5": "5. Återställ projekt",
        "menu_option_6": "6. Avsluta",
        "enter_choice": "Ange val: ",
        "program_descriptions_title": "\n--- Programbeskrivningar ---",
        "program_1_desc_short": "Program 1 (Generera markdowns från CSV)",
        "program_1_desc_long": (
            "Läser skoldata från CSV och använder en mall för att skapa enskilda markdown-filer per skola."
        ),
        "program_2_desc_short": "Program 2 (AI-beskrivningar)",
        "program_2_desc_long": (
            "Tar markdown-filer från Program 1 och skickar innehållet till en AI-tjänst. "
            "AI:n genererar mer detaljerade skolbeskrivningar."
        ),
        "program_3_desc_short": "Program 3 (Generera webbplats)",
        "program_3_desc_long": (
            "Laddar skolnamn från CSV och AI-genererade beskrivningar och genererar en fristående HTML-fil."
        ),
        "select_program_to_describe": "Välj program att beskriva (1, 2, 3, eller 0 för att återgå): ",
        "pipeline_title": "\n--- Kör bearbetningsflöde ---",
        "run_program_1_prompt": "Kör Program 1? (y/n/s, standard y): ",
        "running_program_1": "Kör Program 1...",
        "program_1_complete": "Program 1 klar.",
        "program_1_failed": "Program 1 misslyckades eller hoppade över.",
        "run_program_2_prompt": "Kör Program 2? (y/n/s, standard y): ",
        "running_program_2": "Kör Program 2...",
        "program_2_complete": "Program 2 klar.",
        "program_2_failed": "Program 2 misslyckades eller hoppade över.",
        "program_2_skipped": "Program 2 hoppade över.",
        "run_program_3_prompt": "Kör Program 3? (y/n/s, standard y): ",
        "running_program_3": "Kör Program 3...",
        "program_3_complete": "Program 3 klar.",
        "program_3_failed": "Program 3 misslyckades eller hoppade över.",
        "pipeline_complete": "Bearbetningsflöde klart.",
        "ai_check_title": "\n--- AI-anslutningstest ---",
        "ai_check_prompt": "Kör ett snabbt AI-anslutningstest? (y/n, standard y): ",
        "ai_check_running": "Testar AI-anslutning...",
        "ai_check_ok": "AI-anslutning OK. Fick förväntat svar.",
        "ai_check_fail": "AI-anslutning misslyckades. Kontrollera .env, nätverk och Azure-inställningar.",
        "logs_title": "\n--- Visa loggar ---",
        "no_logs": f"Inga loggfiler hittades i {LOG_DIR}",
        "select_log_prompt": "Ange loggfilens namn att visa (eller 0 för att återgå): ",
        "viewing_log": "Visar logg: ",
        "log_not_found": "Loggfil hittades inte.",
        "exiting": "Avslutar installationsprogrammet.",
        "confirm_recreate_venv": f"VARNING: '{VENV_DIR.name}' finns. Återskapa? (y/n, standard n): ",
        "return_to_menu": "Återgå till huvudmenyn",
        "reset_option": "6. Återställ projekt",
        "reset_confirm": "Radera ALLA genererade filer? (y/n, standard n): ",
        "reset_complete": "Projektet återställt.",
        "reset_cancelled": "Återställning avbröts.",
        "azure_env_intro": "Följande Azure OpenAI-värden krävs för lokal lagring så att programmet kan använda Azure OpenAI.",
        "azure_env_storage": "De sparas i .env-filen. Dessa värden behövs endast för lokal lagring och delas inte.",
        "azure_env_prompt": "Ange värde för {key}: ",
        "quality_suite_ok": "Alla lokala kvalitetskontroller passerade.",
        "quality_suite_fail": "En eller flera lokala kvalitetskontroller misslyckades.",
    },
}


def translate(key: str) -> str:
    """Return the translated string for the given key based on current LANG.

    If translation is missing, the key itself is returned.
    """
    try:
        return TEXTS.get(LANG, TEXTS["en"]).get(key, key)
    except Exception:
        return key


_ = translate


def set_language() -> None:
    """Prompt for UI language and update the global LANG setting."""
    try:
        from src.setup.console_helpers import rprint as _rprint
        from src.setup.ui.prompts import ask_text as _ask
    except Exception:
        _ask = None  # type: ignore
        _rprint = None  # type: ignore

    def _ask_text(prompt: str) -> str:
        """Prompt helper that prefers the prompts module when available.

        Parameters
        ----------
        prompt : str
            Text to present to the user.

        Returns
        -------
        str
            User input string.
        """
        try:
            if _ask is not None:
                return _ask(prompt)
        except Exception:
            pass
        return input(prompt)

    def _print(msg: str) -> None:
        """Print helper that uses the rich-aware rprint when available.

        Parameters
        ----------
        msg : str
            Message to display to the user.
        """
        try:
            if _rprint is not None:
                _rprint(msg)
                return
        except Exception:
            pass
        print(msg)

    new_lang = "en"
    while True:
        try:
            choice = _ask_text(TEXTS["en"]["language_prompt"])
            if choice == "1":
                new_lang = "en"
                break
            if choice == "2":
                new_lang = "sv"
                break
            _print(TEXTS["en"]["invalid_choice"])
        except KeyboardInterrupt:
            _print(TEXTS["en"]["exiting"])
            raise SystemExit from None
        except Exception:
            _print(TEXTS["en"]["invalid_choice"])

    globals()["LANG"] = new_lang
