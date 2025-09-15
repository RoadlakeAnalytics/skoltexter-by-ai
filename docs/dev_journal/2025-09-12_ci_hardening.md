# Utvecklingsjournal: CI-härdning och Ny Hybridstrategi

**Datum:** 2025-09-12
**Status:** Genomförd

## Sammanfattning (TL;DR)

Vi har genomfört en fundamental omarbetning av projektets CI/CD-pipeline och lokala kvalitetssäkring. Målet var att gå från en "strikt" till en "extremt strikt" men samtidigt **intelligent och kostnadseffektiv** process.

De huvudsakliga förändringarna är:

1. **"Shift Left"-filosofi:** En massiv utökning av vår `pre-commit`-konfiguration som nu kör en nästan komplett CI-svit lokalt *innan* kod kan pushas.
2. **Hybrid-CI i GitHub Actions:** Pipelinen är nu uppdelad i två delar:
    * **Snabba verifieringar:** Ett snabbt jobb som körs vid varje pull request för att verifiera att de lokala kontrollerna passerar i en ren miljö.
    * **Djupgående "Canary"-byggen:** Schemalagda, nattliga och veckovisa jobb som kör den fullständiga testmatrisen över Linux, Windows och macOS.
3. **Proaktiv testning:** Vi testar nu proaktivt mot den kommande **Python 3.14 (dev)** för att upptäcka framtida inkompatibiliteter. Detta jobb förväntas misslyckas och är markerat med `continue-on-error`.
4. **Kostnadsoptimering:** Strategin är designad för att drastiskt minska förbrukningen av GitHub Actions-minuter, främst genom att köra de dyra macOS-testerna mer sällan.

## Bakgrund och Mål

Den tidigare CI-pipelinen var bra, men för att detta projekt ska kunna fungera som ett förstklassigt exempel på moderna utvecklingsmetoder, krävdes en mer sofistikerad strategi. Målet var inte bara att lägga till fler verktyg, utan att bygga ett system som demonstrerar en djup förståelse för:

* Effektivitet (snabb feedback vs. djupgående analys).
* Robusthet (testning över flera plattformar).
* Proaktivitet (fånga framtida problem idag).
* Resurshantering (medvetenhet om kostnaden för CI-minuter).

## Detaljerad Genomgång av Förändringar

### 1. Filosofi: "Shift Left" med en Omfattande `pre-commit`-svit

Den största strategiska förändringen är att flytta så mycket av kvalitetssäkringen som möjligt till utvecklarens lokala maskin. Genom att fånga fel *innan* koden når servern sparar vi tid, CI-resurser och minskar frustration.

Vår `.pre-commit-config.yaml` har utökats till att bli en komplett lokal CI-pipeline som körs vid `git commit` och `git push`. Den inkluderar nu:

* **Formatering & Linting:** `black`, `ruff`.
* **Typkontroll:** `mypy --strict`.
* **Säkerhetsanalys:** `semgrep`, `bandit`, `pip-audit`, `gitleaks`.
* **Beroendekontroll:** `pip check`, licens-allowlist, SBOM-validering.
* **Dokumentationstäckning:** `interrogate` med 100% krav.
* **Testning:** `pytest` med två olika slumpmässiga "seeds" för att säkerställa att testordningen inte spelar någon roll.
* **Mutationstestning:** En `mutmut`-grind som säkerställer att inga mutanter överlever, vilket bevisar att våra tester är effektiva.

Detta gör att CI-pipelinen i GitHub Actions kan fokusera på att **verifiera** dessa lokala kontroller och **utöka** dem med plattformsspecifik testning.

### 2. Ny CI-Struktur: En Hybridmodell

CI-pipelinen i `.github/workflows/ci.yml` är nu uppdelad i tre oberoende jobb med olika triggers:

* **`validate-local-checks` (vid PR/Push):**
  * **Syfte:** Att snabbt verifiera att den lokala `pre-commit`-sviten passerar i en ren Ubuntu-miljö.
  * **Trigger:** `on: [pull_request, push]`.
  * **Resultat:** Ger snabb feedback (< 5 minuter) på om en ändring är säker att granska.

* **`nightly-matrix` (Dagligen):**
  * **Syfte:** Att köra den fullständiga testsviten mot en matris av **Linux och Windows** för alla relevanta Python-versioner (3.11-3.14).
  * **Trigger:** `schedule: cron: "0 2 * * *"` (02:00 UTC varje natt).
  * **Resultat:** Fångar plattformsspecifika buggar och regressioner i beroenden som kan ha uppstått över tid.

* **`weekly-macos-matrix` (Veckovis):**
  * **Syfte:** Samma som ovan, men för **macOS**.
  * **Trigger:** `schedule: cron: "0 3 * * 1"` (03:00 UTC varje måndag).
  * **Resultat:** Garanterar full plattformskompatibilitet. Genom att köra detta jobb mer sällan sparar vi avsevärt på CI-minuter, då macOS-runners har en 10x kostnadsmultiplikator.

### 3. Proaktiv Testning: Python 3.14 "Canary"

I de schemalagda matrisjobben inkluderar vi nu Python 3.14. Vi är medvetna om att viktiga beroenden som `pandas` ännu inte har stöd för denna version.

* **`allow-prereleases: true`:** Används i `actions/setup-python` för att kunna hämta alpha/beta-versioner av Python.
* **`continue-on-error: true`:** Detta är den avgörande inställningen. Vi *förväntar* oss att detta jobb misslyckas. Genom att sätta denna flagga säkerställer vi att ett misslyckande på 3.14 inte markerar hela den nattliga körningen som misslyckad.

Syftet med detta jobb är inte att få en grön bock, utan att fungera som ett **automatiskt bevakningssystem**. Den dagen `pandas` och andra bibliotek släpper stöd för 3.14 kommer detta jobb att sluta misslyckas på installationssteget, vilket ger oss en tidig signal om att vi kan börja anpassa vår kod.

### 4. Kostnads- och Resursoptimering

Förutom att separera macOS-körningarna har vi implementerat flera andra "best practices":

* **`concurrency: cancel-in-progress: true`:** Om en ny push görs till en pull request avbryts den föregående, pågående CI-körningen automatiskt. Detta förhindrar att man slösar minuter på att testa utdaterad kod.
* **`paths-ignore`:** CI-körningar triggas inte alls för ändringar som enbart rör filer som `README.md` eller annan dokumentation.
* **`permissions: contents: read`:** Vi sätter minimala behörigheter på global nivå och ger endast utökade rättigheter till de jobb som specifikt behöver dem (inte aktuellt just nu, men en bra grundprincip).

## Resultat

Den nya CI-strategin är en dramatisk förbättring. Den är snabbare för den dagliga utvecklingen, mer grundlig i sin testning, proaktiv inför framtiden och smartare med sina resurser. Den fungerar nu som ett utmärkt exempel på hur man bygger en professionell och mogen CI/CD-pipeline för ett modernt Python-projekt.
