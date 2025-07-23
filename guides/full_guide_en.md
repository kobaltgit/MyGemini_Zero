# [START OF SECTION: API_KEY]

### 🔑 How to Get and Set a Google API Key

An API key is your personal pass to the Gemini neural network. The bot needs it to send requests on your behalf. It's secure: the bot encrypts and stores your key, never sharing it with third parties.

#### ❗ Important Note for Users from Certain Regions

Access to Google AI services may sometimes be restricted depending on your geographical location. If you see an error, an unavailability message, or a blank page when clicking the links below, try the following:

*   **Use a special extension for your browser.** There are extensions that help bypass regional restrictions and provide access to international websites. You can find them in the official extension store for your browser (Chrome, Firefox, etc.).
*   **Use services that change your network connection.** Such programs route your internet traffic through a server in another country, allowing you to "get around" geographical blocks.

After activating one of these tools, refresh the page.

#### Step-by-Step Instructions

1.  **Go to Google AI Studio:** Navigate to the official [Google AI Studio](https://makersuite.google.com/app) website. You will need to sign in with your Google account.

2.  **Navigate to API key creation:** In the menu on the left, find the **"Get API key"** option or use the direct link: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey).

3.  **Create the key:** Click the blue button **"Create API key in new project"**.

    ![Step 3 - create key button](https://i.ibb.co/hJm9HHhM/Screenshot-of-Chat-Google-AI-Studio.jpg)

4.  **Copy the key:** After a few seconds, your new key (a long string of characters) will appear in the list. Click the "copy" icon next to it.

    ![Step 4 - generated key](https://i.ibb.co/Kc0cbTmL/Screenshot-of-Get-API-key-Google-AI-Studio.jpg)

5.  **Set the key in the bot:**
    *   Return to this chat.
    *   Send the `/set_api_key` command.
    *   Paste the copied key into the message box and send it.

The bot will verify the key, and if everything is correct, you can start chatting!

# [END OF SECTION: API_KEY]

---

# [START OF SECTION: FEATURES]

### 🚀 Bot Features

After setting up the API key, you gain access to the following features:

#### 🧠 Main Chat
Simply type your questions or tasks in the chat. The bot maintains the context of the conversation within the active dialog.

#### 🖼️ Image Analysis
Send an image to the bot (as a photo, not a file). You can add a caption to the image to specify your request, for example: "What breed is this dog?" or "Create a recipe from these ingredients."

#### 🗂️ Dialog Management (`/dialogs`)
The bot allows you to have multiple independent conversations at the same time. This is useful for keeping the contexts of different tasks (e.g., "Work" and "Travel") separate.
*   **Create:** Click "➕ Create New" to start a new conversation from scratch.
*   **Switch:** Simply click on a dialog's name in the list to make it active. Its context will be loaded immediately.
*   **Rename:** Each dialog has an "✏️" button that lets you give it a new, more descriptive name.
*   **Delete:** Click "❌" next to an inactive dialog to delete it along with its entire history. **The active dialog cannot be deleted.**

#### 📜 Message History (`/history`)
You can view the entire conversation with the bot in the current active dialog for any selected date.

#### 📊 Usage Statistics (`/usage`)
This command shows how many tokens have been used for generating responses today and for the current month, as well as an estimated cost in USD based on public Google tariffs.

#### 👤 My Account (`/account`)
This section gathers all information about your profile: your "title" in the bot, the number of messages sent, current settings, and a brief analysis of the topics you most frequently discuss in the current dialog.

# [END OF SECTION: FEATURES]

---

# [START OF SECTION: SETTINGS]

### ⚙️ Settings (`/settings`)

In this menu, you can fine-tune the bot's behavior to suit your needs.

#### 🎭 Assistant Persona
This is the most important setting. The "Persona" defines the role the bot will play in communication. For example, you can turn it into a "Python Expert," a "Financial Advisor," or a "Historian." Choosing a persona dramatically changes the style and depth of the answers. If a persona is selected, the "Communication Style" setting below will be ignored.

#### 🧠 Gemini Model
Here you can choose which version of the neural network to use.
*   `gemini-1.5-flash`: A fast, efficient, and very inexpensive model, great for most tasks. It is used by default.
*   `gemini-1.5-pro`: A more powerful and "smarter" model, better at complex creative and analytical tasks, but it is slower and more expensive.

#### 👔 Communication Style
This setting only works if "Default Assistant" is selected as the "Persona." It allows you to set the general tone of the answers:
*   **Formal:** A strict and business-like style.
*   **Informal:** Friendly and simple language.
*   **Concise:** Answers to the point, without fluff.
*   **Detailed:** The most comprehensive explanations.

#### 🌐 Interface Language
You can switch the language of all bot buttons and system messages between Russian and English. This does not affect the language in which you communicate with Gemini.

# [END OF SECTION: SETTINGS]