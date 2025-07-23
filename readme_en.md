# MyGemini: Your Personal Gemini-Powered Telegram Assistant

### [Русская версия README](readme.md)

[
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square)
](https://www.python.org/downloads/)
[
![pyTelegramBotAPI](https://img.shields.io/badge/pyTelegramBotAPI-4.15.0+-brightgreen.svg?style=flat-square)
](https://github.com/eternnoir/pyTelegramBotAPI)
[
![Gemini API](https://img.shields.io/badge/Gemini_API-Via_REST-orange.svg?style=flat-square)
](https://ai.google.dev/)
[
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)
](https://opensource.org/licenses/MIT)
[
![aiohttp](https://img.shields.io/badge/aiohttp-3.9.5+-red.svg?style=flat-square)
](https://docs.aiohttp.org/en/stable/)
[
![Cryptography](https://img.shields.io/badge/Cryptography-43.0.0+-gold.svg?style=flat-square)
](https://github.com/pyca/cryptography)
[
![python-dotenv](https://img.shields.io/badge/python--dotenv-1.0.1+-silver.svg?style=flat-square)
](https://github.com/theskumar/python-dotenv)
[
![PyYAML](https://img.shields.io/badge/PyYAML-6.0.1+-indigo.svg?style=flat-square)
](https://pyyaml.org/)
[
![SQLite3](https://img.shields.io/badge/SQLite-3-magenta.svg?style=flat-square)
](https://www.sqlite.org/index.html)
[
![Pillow](https://img.shields.io/badge/Pillow-10.3.0+-darkgreen.svg?style=flat-square)
](https://python-pillow.org/)
[
![cachetools](https://img.shields.io/badge/cachetools-5.3.3+-brown.svg?style=flat-square)
](https://github.com/tkem/cachetools)
[
![LangChain](https://img.shields.io/badge/LangChain-0.2.0+-purple.svg?style=flat-square)
](https://www.langchain.com/)
[
![Telegramify-Markdown](https://img.shields.io/badge/Telegramify--Markdown-0.2.1+-violet?style=flat-square)
](https://github.com/sudoskys/telegramify-markdown)


## Project Description


**MyGemini** is an asynchronous, multilingual Telegram bot that serves as your personal and secure gateway to the capabilities of the Google Gemini API. Unlike public bots, MyGemini uses **your own API key**, giving you full control over quotas and costs.


The bot is designed with an emphasis on privacy and flexibility. You can conduct **multiple independent dialogues** simultaneously, ensuring that contexts for different tasks do not mix. And thanks to the **"personas"** system, you can transform the bot from a regular assistant into a specialized expert: a programmer, a financial advisor, or a historian.


### **[Start using the bot](https://t.me/mgem_bot)**
<img src="https://i.ibb.co/N62z1kWc/Screenshot-35.png" alt="Screenshot-35" border="0">


## 🚀 Key Features


### For Users


*   **Personal API Key:** Works with your personal Google AI key, ensuring privacy and control over API usage.
*   **Secure Storage:** User API keys are securely encrypted before being saved to the database.
*   **Multi-Context Dialogues:** Create, switch, rename, and delete independent dialogues to prevent contexts from different topics from overlapping.
*   **Flexible Personalization:**
    *   **Persona Selection:** Assign a role to the bot (e.g., "Python Expert", "Copywriter"), and it will respond accordingly.
    *   **Model Selection:** Switch between the fast `gemini-1.5-flash` and powerful `gemini-1.5-pro` depending on the task.
    *   **Language Change:** The bot's interface supports Russian and English languages.
*   **Intelligent Communication:** Answers to questions and text generation based on the Google Gemini model, taking into account the selected persona and dialogue history.
*   **Image Analysis:** Recognition and description of image content with the ability to ask a clarifying question.
*   **Internet Search:** To provide up-to-date information, the bot can access Google Search. This feature is enabled automatically if the selected model supports it. Currently, search is available for the following models: `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-2.0-pro-experimental`, and `gemini-2.5-pro`.
*   **Detailed Help:** Built-in guide (`/help_guide`) helps new users get started quickly, including a step-by-step guide on obtaining an API key.
*   **Personal Account and Statistics:**
    *   `/account`: View your "title" in the bot, overall statistics, and a brief analysis of topics in the current dialogue.
    *   `/usage`: Track token usage statistics and approximate cost of requests.


### 👑 For Administrator


The bot includes a powerful admin panel (`/admin`) for full control over its operation:


*   **Global Statistics:** View total user count, activity over the last 7 days, and number of blocked users.
*   **User Management:**
    *   Search for a user by ID to view detailed information (registration date, language, status).
    *   Block and unblock users.
    *   Force-reset a user's API key in case of compromise.
*   **Communication:**
    *   **Mass Mailing:** Send messages to all bot users.
    *   **Individual Messages:** Send a private message to any user via the interactive menu or using the `/reply` command.
*   **Data Export:** Export a list of all users to a `.csv` file.
*   **Maintenance Mode:** Temporarily disable the bot for everyone except the administrator during maintenance work.


## Technologies*   **Python 3.10+:** Primary programming language.
*   **pyTelegramBotAPI (async):** Asynchronous library for interacting with the Telegram Bot API.
*   **aiohttp:** For making direct, non-blocking HTTP requests to the Gemini API.
*   **Cryptography:** For secure encryption of user API keys.
*   **python-dotenv:** For managing configuration via `.env` files.
*   **PyYAML:** For logging system configuration.
*   **sqlite3:** Built-in SQLite database for storing user data and message history.
*   **Pillow:** For image processing before sending to the API.
*   **cachetools:** For LRU caching of dialogue history and preventing memory leaks.
*   **langchain:** For reliable semantic splitting of long texts and code blocks into chunks.
*   **telegramify-markdown:** For correct conversion of Markdown to Telegram MarkdownV2 format, with all special characters escaped.

## Setup and Launch

### Prerequisites

*   **Python 3.10 or higher.**
*   **pip:** Python package manager.
*   **Git:** For cloning the repository.

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/kobaltgit/MyGemini]
    cd MyGemini
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # for Linux/macOS
    # or
    venv\Scripts\activate  # for Windows
    ```

3.  **Install project dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Generate an encryption key:**
    Create a temporary file `generate_key.py` and run it to obtain a secret key:
    ```python
    # File: generate_key.py
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    print(f"ENCRYPTION_KEY={key.decode()}")
    ```
    ```bash
    python generate_key.py
    ```
    Copy the resulting string (`ENCRYPTION_KEY=...`). Afterwards, the `generate_key.py` file can be deleted.

5.  **Configure environment variables:**
    Create a `.env` file in the project's root directory and add the following variables to it:

    ```env
    # Your Telegram bot token from @BotFather
    BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11


    # Your Telegram User ID for admin notifications (optional)
    ADMIN_USER_ID=123456789


    # Encryption key you generated in the previous step
    ENCRYPTION_KEY=..._ваша_сгенерированная_строка_...


    # Gemini model the bot will use (optional)
    GEMINI_MODEL_NAME=gemini-1.5-flash-latest


    # Donation link (optional, if you want to add a "Support" button)
    DONATION_URL=https://pay.example.com/your_donation_page
    ```

### Launching the Bot

Launch the bot by running the following command in the terminal:

```bash
python main.py
```

After launching, the bot is ready for use. Find it on Telegram and send the /start command.

## First Use
1. On the first launch, the bot will ask you to set up an API key.
2. Use the `/set_api_key` command.
3. Send your API key from [Google AI Studio](https://makersuite.google.com/app/apikey) to the bot.
4. After successful key setup, you will be able to fully use the bot.## Core Commands
*   `/start` - Restart the bot.
*   `/help_guide` - Show the full guide to all bot functions.
*   `/apikey_info` - Show instructions for obtaining an API key.
*   `/dialogs` - Open the dialog management menu.
*   `/settings` - Open the settings menu (persona, model, language selection).
*   `/usage` - Show token usage statistics.
*   `/account` - Open personal account.
*   `/history` - View message history in the current dialog.
*   `/reset` - Reset the context of the current dialog.

## Directory Structure
```
MyGemini/
├── .env                    # File with environment variables (secrets, tokens). Created manually.
├── logger_config.py        # Setup and configuration of the logging system.
├── main.py                 # Main file to run the bot, initialization, and start of polling.
├── readme.md               # This file. Project documentation.
├── requirements.txt        # List of external libraries and project dependencies.
│
├── config/
│   ├── logging.yaml        # YAML configuration for the logger (formatters, handlers, levels).
│   └── settings.py         # Loading environment variables and defining global constants.
│
├── database/
│   ├── db_manager.py       # Database manager. Contains all functions for working with SQLite.
│   └── bot_database.db     # SQLite database file (created automatically).
│
├── features/
│   └── personal_account.py # Logic for generating the 'Personal Account' page (/account).
│
├── guides/
│   ├── full_guide_ru.md    # Full bot guide in Russian.
│   └── full_guide_en.md    # Full bot guide in English.
│
├── handlers/
│   ├── admin_handlers.py     # Handlers for commands and callback queries for the admin panel.
│   ├── callback_handlers.py  # Handlers for all callback queries from inline buttons (except admin ones).
│   ├── command_handlers.py   # Handlers for command messages (/start, /help, /settings, etc.).
│   ├── decorators.py         # Decorators used in handlers (e.g., @admin_required).
│   ├── message_handlers.py   # Universal handler for all incoming messages, routing by state.
│   └── telegram_helpers.py   # Helper functions for working with the Telegram API (sending, editing messages).
│
├── logs/                   # Directory for log files (created automatically).
│
├── services/
│   ├── error_parser.py     # Parser for Gemini API errors to convert them into user-friendly messages.
│   └── gemini_service.py     # Service for interacting with the Google Gemini API (sending requests, managing history).
│
└── utils/
    ├── analysis_helpers.py   # Functions for text analysis (extracting topics from chat history).
    ├── crypto_helpers.py     # Functions for encrypting and decrypting data (API keys).
    ├── guide_manager.py      # Manager for loading and providing help texts from files.
    ├── localization.py       # Localization module. Contains all interface texts in different languages.
    ├── markup_helpers.py     # Functions for creating all keyboards (reply and inline) in the bot.
    └── text_helpers.py       # Helper functions for text processing (cleaning from Markdown, etc.).
```

## Logging System
Logging is configured via the file `config/logging.yaml`. Logs are separated by files and saved in the directory `logs/`:*   **bot_general.log** - general application operation logs.
*   **database.log** - logs related to database operations.
*   **gemini_api.log** - logs of requests to the Gemini API.
*   **user_messages.log** - logs of incoming messages from users.
## License
* This project is licensed under the MIT License.
## Support and Feedback
If you have questions, suggestions, or found errors, please create an issue in the GitHub repository or contact [me](mailto:kobaltmail@gmail.com).
## Enjoy using the bot!