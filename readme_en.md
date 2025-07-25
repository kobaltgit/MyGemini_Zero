# MyGemini Zero: Your Private AI Assistant with Long-Term Memory

### [Читать на русском](readme.md)

[
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square)
](https://www.python.org/downloads/)
[
![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg?style=flat-square)
](https://www.gnu.org/licenses/agpl-3.0)
[
![Security](https://img.shields.io/badge/Security-Zero--Knowledge-red.svg?style=flat-square)
]()
[
![Memory](https://img.shields.io/badge/Memory-Vector_DB-purple.svg?style=flat-square)
]()


**MyGemini Zero** is not just another Telegram bot. It's your personal, secure, and truly intelligent gateway to the capabilities of Google Gemini, built on the principles of **complete privacy and long-term memory**.


Unlike standard chats that "forget" everything after each conversation, MyGemini Zero transforms the neural network from a genius with amnesia into your personal assistant who **remembers, learns, and adapts** to you. And all of this comes with a cryptographic guarantee that no one, not even service administrators, can read your data.

---

## Access Model: Paid Service, Free Alternative & Open Source

**MyGemini Zero is a paid subscription service.** We believe in openness, so we offer you three ways to proceed:

1.  **🚀 Hosted Service (Paid):** Get all the benefits of MyGemini Zero without the technical hassle. Stability, updates, and support are all included.
    *   **[➡️ Go to the MyGemini Zero Bot](https://t.me/mgemz_bot)** (Subscription Required).

2.  **🆓 Free Alternative:** If you don't need long-term memory and Zero-Knowledge encryption, you can use our basic **MyGemini** bot. It's completely free and runs on your personal API key.
    *   **[➡️ Go to the free MyGemini Bot](https://t.me/mgem_bot)**.

3.  **💻 DIY Self-Hosting (Free):** If you are a technical user, you can deploy this bot on your own server for free using our open-source code.
    *   **[➡️ Go to the Setup Guide](#️-for-enthusiasts-self-hosting)**


### **[Start using the bot (coming soon)](https://t.me/mgem_bot)**
<img src="https://i.ibb.co/NdbvMTWJ/Screenshot-34.png" alt="Screenshot-34" border="0">


## 🌟 I have ChatGPT/Gemini. Why should I pay for your bot?


This is the main question, and we have four answers:


#### 1. **Memory: Your Personal "Second Brain"**
*   **Problem:** Standard chatbots don't remember your past conversations. You are forced to repeat context, explaining your goals and projects over and over again.
*   **Our Solution:** MyGemini Zero is integrated with a **personal vector database**. Every one of your dialogues, uploaded documents, or important thoughts transforms into a "memory." When you ask a new question, the bot automatically finds relevant context from the past and adds it to the query.
    *   **Result:** You can ask "What were the key risks in the project we discussed last week?" or "Remind me of the main ideas from that marketing article," and the bot will understand what you're referring to. It becomes your personal, always-available "second brain."


#### 2. **Privacy: Zero-Knowledge Architecture**
*   **Problem:** When using third-party bots, you entrust your data not only to Google/OpenAI but also to the intermediary bot developer. You don't know how they store your dialogues or who has access to them.
*   **Our Solution:** We use an architecture where all your data (history, files, API key) is encrypted with a **master password** that **only you** know.
    *   **Result:** As the service creators, we **cryptographically cannot** read your data. We simply do not have the key to your "digital safe." If you forget your password, your data will be lost forever, as no one will be able to recover it. This offers maximum privacy in exchange for your personal responsibility.


#### 3. **Personalization: A Bot That Knows You**
*   **Problem:** Standard models provide generic answers, not taking into account your profession, communication style, or goals.
*   **Our Solution:** Upon the first launch, the bot invites you to fill out a brief profile questionnaire. This information becomes the foundation for its operation. Combined with long-term memory, this allows the bot to provide answers specifically tailored to you.
    *   **Result:** An answer for a developer will contain code and technical details, while an answer for a manager will include structure, timelines, and key metrics. The bot speaks your language.#### 4. **Convenience: A Ready-Made "Turnkey" Service**
*   **Problem:** Self-configuring and maintaining such a complex tool requires time, technical knowledge, and constant upkeep.
*   **Our Solution:** We take care of all of this. You don't need to delve into servers, databases, or updates. You receive a ready-to-use, stable, and constantly evolving service.
    *   **Result:** You simply enjoy all the benefits, saving dozens of hours on technical routine. You pay not for the code (it's open-source), but for **convenience, stability, and security**.

---

## 🔐 How Security Works (Zero-Knowledge)?

Imagine your data is a treasure in a safe.

1.  **You create a unique key:** Upon registration, you create a **master password**. This password is the only physical key to your safe.
2.  **We do not store your key:** We do not save your password. We only store its encrypted "fingerprint" (hash), from which the password itself cannot be restored.
3.  **Encryption key is created "on the fly":** Each time you enter your password to unlock a session, a temporary encryption key is generated from it and your personal "salt". It exists only in RAM and disappears after the session ends.
4.  **All data is encrypted:** Everything is encrypted with this temporary key:
    *   Your Google API key.
    *   The history of all your dialogues.
    *   Your profile data.
    *   Your long-term memory (vector database).

> **Transparency is our principle.** We protect your data from us (the intermediary). But the final request (your prompt + context from memory) is sent to Google Gemini in unencrypted form. Our service is for those who trust Google but do not want to trust third-party developers.

#### Clarification: What about long-term memory (vector database)?

This is an important technical nuance that we are explaining for full transparency. For its operation, long-term memory must store text fragments (chunks) in an **unencrypted form**.

**Why?**

Imagine memory as a library catalog. For you to quickly find information not only by general meaning (semantic search) but also by **exact keyword** (e.g., to find all mentions of "Project Quantum"), the system must "see" the text of these fragments.

If we were to encrypt them, keyword search would cease to function. This is a conscious compromise made to preserve important functionality.

However, the **context remains protected**:
1.  **Isolation:** The memory for each of your dialogues is stored in a separate, isolated "collection," inaccessible to other dialogues or users.
2.  **Communication Security:** All other information — your API key, the full dialogue history in the main database, your profile — is securely encrypted with your master password.
3.  **No Direct Link:** The vector database contains no direct information about which user owns a particular fragment.

We chose this approach to provide you with a powerful search tool while maintaining the core principle: **no one but you holds the key to your complete "digital vault"**.

#### Panic Password

For emergency situations, you can set an optional *panic password*. If you enter it instead of your main password to unlock the session, the bot will pretend to unlock successfully, but in reality, it will **immediately and irreversibly delete all your message history and long-term memory content**.

This is a "plausible deniability" feature that provides an extra layer of protection in critical situations.

---

## 🚀 Key Features

*   **🧠 Long-term memory:** Remembers the context of all your dialogues. You can refer to past information and **upload files** (`.txt`, `.md`) directly into a dialogue's memory using the `/memorize` command.
*   **🔐 Zero-Knowledge Architecture:** Cryptographic data protection with the user's master password, plus an optional **panic password** for emergency data deletion.
*   **👤 Deep personalization:** Accounts for your profile (role, goals, style) to adapt responses.
*   **🗂️ Multi-context dialogues:** Create, switch between, and rename independent dialogues to prevent different topics' contexts from overlapping.
*   **📄 Data Management:** You can **archive old messages**, replacing them with concise summaries to save space, or **completely erase all your data** without deleting your account.
*   **🖼️ Image analysis:** Recognition and description of image content with the ability to ask clarifying questions.
*   **🌐 Internet search:** Automatic access to Google for providing up-to-date information (for supported models).
*   **👑 Powerful admin panel:** For owners of their own instances — complete control over the bot.

---

## 🛠️ Technologies

*   **Python 3.10+** and **pyTelegramBotAPI (async)**
*   **Cryptography, bcrypt, PBKDF2:** For implementing Zero-Knowledge architecture.
*   **LangChain & ChromaDB:** For implementing long-term memory and semantic search.
*   **SQLite:** For storing encrypted data.
*   **aiohttp, python-dotenv, PyYAML, Pillow, cachetools, telegramify-markdown**

---

## ⚙️ For Enthusiasts: Self-Hosting

Even though we offer a ready-made service, we believe in openness. You can deploy your own instance of the bot for free.

### Prerequisites
*   **Python 3.10 or higher.**
*   **Git**

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/kobaltgit/MyGemini_Zero]
    cd MyGemini_Zero
    ```
    

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # for Linux/macOS
    # or
    venv\Scripts\activate  # for Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```4. **Configure environment variables:**
    Create a `.env` file in the project's root directory and add your Telegram bot token `BOT_TOKEN` and your Telegram ID `ADMIN_USER_ID` to it.


    ```env
    # Токен вашего Telegram-бота от @BotFather
    BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11


    # Ваш Telegram User ID для админских прав
    ADMIN_USER_ID=123456789
    ```


### Running the bot
```bash
python main.py
```
After launching, find the bot in Telegram and send the `/start` command. It will guide you through the process of creating a master password and configuring the Google API key.


---


## 💬 Core Commands
*   `/start` - Restart the bot or unlock the session.
*   `/logout` - Lock the session (requires password entry for the next action).
*   `/profile` - View and modify your profile.
*   `/dialogs` - Open the dialog management menu.
*   `/settings` - Open the settings menu (persona, model, language selection).
*   `/usage` - Show Google API token usage statistics.
*   `/history` - View message history in the current dialog.
*   `/reset` - Reset the *short-term* context of the current dialog (does not affect long-term memory).
*   `/memorize` - Upload a text file (`.txt`, `.md`) into long-term memory.
*   `/archive` - Archive old messages in the current dialog.


---

## License

This project is distributed under the **GNU Affero General Public License v3.0 (AGPLv3)**.

A key condition of this license is that if you use this code to create a public network service (for example, your own Telegram bot based on it), you are obliged to provide users of this service with access to the full source code, including all your modifications.

This protects the project from being used in closed commercial products and ensures that all improvements made by the community are returned to the community.

The full text of the license can be found in the [LICENSE](LICENSE) file.

## 📞 Support and Feedback
If you have questions, suggestions, or found bugs, please create an issue in the GitHub repository or contact [me](mailto:kobaltmail@gmail.com).


## Happy using!