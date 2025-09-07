# Byt LLM-leverantör: Konfigurationsguide

Denna fil beskriver steg-för-steg hur du anpassar projektets AI-processor (`program2_ai_processor.py`) för att använda olika LLM-leverantörer istället för Azure OpenAI (GPT‑4o), enligt CHATGPT.

>Jag föreställer mig att om du har en API nyckel så har du också möjlighet att klistra in all kod i lämplig chatt för eventuell felsökning och ytterligare inställningar. Det är sannolikt inte mycket som kommer behöva ändras i de flesta fall :)

---

## 1. Vanliga OpenAI

1. **Installera paketet**

    ```bash
    pip install openai
    ```

2. **Sätt API-nyckel**

    Lägg till i `.env`:
    ```ini
    OPENAI_API_KEY="din_openai_api_nyckel"
    ```

3. **Ändra import och klient**

    I `program2_ai_processor.py`, ersätt Azure-config och anrop med OpenAI-klient:

    ```python
    import openai

    class OpenAIConfig:
        def __init__(self):
            self.api_key = os.getenv("OPENAI_API_KEY")
            openai.api_key = self.api_key

    async def call_openai_api(...):
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=payload["messages"],
            temperature=self.config.temperature,
            max_tokens=AI_PAYLOAD_MAX_TOKENS,
        )
        content = response.choices[0].message.content
        return True, content, response.to_dict()
    ```

---

## 2. AI Studio (Gemini)

1. **Installera Google Cloud SDK**

    ```bash
    pip install google-ai-generativt
    ```

2. **Sätt upp autentisering**

    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/nyckel.json"
    ```

3. **Anpassa klient**

    ```python
    from google.ai import generativt

    class GeminiConfig:
        def __init__(self):
            self.client = generativt.ChatServiceClient()

    async def call_openai_api(...):  # byt namn vid behov
        chat = self.client.chat(
            model="gemini-pro",
            temperature=self.config.temperature,
            messages=[
                {"author": "system", "content": system_content},
                {"author": "user",   "content": user_content},
            ],
        )
        content = chat.choices[0].content
        return True, content, chat
    ```

---

## 3. Claude (Anthropic)

1. **Installera paketet**

    ```bash
    pip install anthropic
    ```

2. **Sätt API-nyckel**

    I `.env`:
    ```ini
    ANTHROPIC_API_KEY="din_anthropic_api_nyckel"
    ```

3. **Anpassa anropet**

    ```python
    import anthropic

    class ClaudeConfig:
        def __init__(self):
            self.client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def call_openai_api(...):
        response = self.config.client.create_chat_completion(
            model="claude-2",
            messages=[
                {"role": "system",  "content": system_content},
                {"role": "user",    "content": user_content},
            ],
            temperature=self.config.temperature,
            max_tokens_to_sample=AI_PAYLOAD_MAX_TOKENS,
        )
        content = response.completion
        return True, content, response
    ```

---

## 4. OpenRouter

1. **Installera paketet**

    ```bash
    pip install openrouter
    ```

2. **Sätt API-nyckel**

    I `.env`:
    ```ini
    OR_API_KEY="din_openrouter_api_nyckel"
    ```

3. **Anpassa klient**

    ```python
    from openrouter import OpenRouter

    class OpenRouterConfig:
        def __init__(self):
            self.client = OpenRouter(api_key=os.getenv("OR_API_KEY"))

    async def call_openai_api(...):
        response = self.config.client.chat.completions.create(
            model="gpt-4o",
            messages=payload["messages"],
            temperature=self.config.temperature,
            max_tokens=AI_PAYLOAD_MAX_TOKENS,
        )
        content = response.choices[0].message.content
        return True, content, response
    ```

---

## 5. Lokal LLM via Ollama

1. **Installera Ollama**

    ```bash
    ollama pull llama2
    pip install ollama
    ```

2. **Anrop till lokal modell**

    ```python
    import ollama

    class OllamaConfig:
        def __init__(self):
            self.model = "llama2"

    async def call_openai_api(...):
        chat = ollama.chat(
            model=self.config.model,
            messages=payload["messages"]
        )
        content = chat["choices"][0]["message"]["content"]
        return True, content, chat
    ```
