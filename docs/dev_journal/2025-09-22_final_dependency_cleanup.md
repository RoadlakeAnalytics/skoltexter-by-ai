# Slutfas: Eliminering av Sista Aktiva Shim-beroenden

**Datum:** 2025-09-22 00:16

## 1. Sammanfattning

Efter en misslyckad audit-körning som identifierade kvarvarande aktiva beroenden till `src.setup.app`, genomfördes denna operation för att eliminera de sista kritiska referenserna i produktionskoden.

## 2. Genomförda Åtgärder

1.  **Refaktorering av `setup_project.py`:**
    *   **Före:** `from src.setup.app import run as app_run`
    *   **Efter:** `from src.setup.app_runner import run as app_run`
    *   **Motivering:** Startpunkten pekar nu direkt på den refaktorerade runner-modulen istället för via shimmen.

2.  **Refaktorering av `src/setup/venv_manager.py`:**
    *   **Före:** `argv = [str(venv_python), "-m", "src.setup.app"]`
    *   **Efter:** `argv = [str(venv_python), "-m", "setup_project"]`
    *   **Motivering:** Den själv-omstartande logiken använder nu den rena, minimala `setup_project.py`-launchern, vilket helt tar bort beroendet till shimmen.

## 3. Verifiering

Hela testsviten kördes med `pytest`. Samtliga tester passerade, vilket bekräftar att ändringarna var säkra.

## 4. Resultat

Alla kända **aktiva kodberoenden** till `src.setup.app` är nu eliminerade. Kodbasen är redo för den slutgiltiga borttagningen av shim-filerna.

