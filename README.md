
# 🧠 AI-Powered Postgres Chatbot

This is an AI chatbot built using **LangChain**, **Streamlit**, and **PostgreSQL**. It allows users to ask natural language questions that are translated into SQL queries using an LLM (like OpenAI's GPT-4), executed on a connected PostgreSQL database, and then returns the results in an easy-to-understand format.

---

## 📦 Features

- 🗣️ Ask questions in plain English
- 📊 Auto-generates SQL queries using an LLM
- 🧮 Executes queries on a connected PostgreSQL database
- 📋 Returns results in a readable table format
- 🖥️ Streamlit-based local web interface
- 🧠 Powered by LangChain + OpenAI

---

## 🚀 Tech Stack

- **Frontend/UI**: Streamlit
- **LLM Orchestration**: LangChain
- **LLM Provider**: OpenAI (ChatGPT / GPT-4)
- **Database**: PostgreSQL
- **Backend**: Python

---

## 🔧 Prerequisites

Make sure you have the following installed:

- Python 3.8 or higher
- PostgreSQL (local or remote)
- Git
- An OpenAI API Key

---

## 📥 Clone the Repository

```bash
git clone https://github.com/DefinitelyNBN/ai-postgres-chatbot.git
cd ai-postgres-chatbot
````

---

## 🐍 Set Up Virtual Environment (Optional but Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

---

## 📦 Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Setup

Create a `.env` file in the root of the project with the following values:

```env
OPENAI_API_KEY=your_openai_api_key_here

# PostgreSQL credentials
PGHOST=localhost
PGPORT=5432
PGDATABASE=your_database_name
PGUSER=your_database_user
PGPASSWORD=your_database_password
```

> ⚠️ Make sure your PostgreSQL server is running and accessible with the above credentials.

If you don’t have a database yet, you can create one using:

```bash
createdb chatbot_db
```

Then, you can connect to it using `psql` or any GUI like DBeaver or pgAdmin and create your schema/table for the chatbot to query.

---

## ▶️ Run the Application

Once everything is configured, launch the chatbot using:

```bash
streamlit run app.py
```

This will open a local Streamlit interface in your browser (usually at [http://localhost:8501](http://localhost:8501)).

---

## 🧪 Sample Usage

* **User Input**: “Show me the number of users who signed up this month.”
* **Generated SQL**: `SELECT COUNT(*) FROM users WHERE signup_date >= DATE_TRUNC('month', CURRENT_DATE);`
* **Output**: Displays the result in a table.

> You can modify the prompt/template inside the code to tailor it to your database schema.

---

## 🛠️ Project Structure

```
ai-postgres-chatbot/
│
├── app.py               # Main Streamlit app entry point
├── db.py                # PostgreSQL connection & querying logic
├── agent.py             # LangChain SQLAgent initialization
├── prompt.py            # Custom prompt template (optional)
├── requirements.txt     # All dependencies
└── .env                 # Your API/database credentials (not pushed to GitHub)
```

---

## 🧩 Customize for Your Database

1. Modify the prompt inside `prompt.py` if you want to add schema context or improve the quality of generated SQL.
2. If you have specific tables or relationships, include them in the system prompt.
3. Use sample SQL queries in your schema to give better context to the LLM.

---

## 📚 Additional Tips

* Use GPT-4 for better SQL generation (change model name in `agent.py`).
* If Streamlit fails to start, check for `.env` misconfiguration or missing packages.
* Always test the generated SQL before using it in production environments.

---

## 🛡️ Disclaimer

This app is a prototype and should not be connected directly to production databases without validation or sandboxing. Generated SQL should be reviewed if running in a critical environment.

---

## 🙋‍♂️ Author

Made by [DefinitelyNBN](https://github.com/DefinitelyNBN)

---

## 🪪 License

This project is licensed under the MIT License.

