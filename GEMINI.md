# GEMINI.md: Sanskara AI Project

## Project Overview

This is the repository for Sanskara AI, a multi-agent AI wedding planner specializing in Indian weddings. The system is designed to be a collaborative tool for couples and their families to plan a wedding, with a focus on Indian traditions.

**Key Technologies:**

*   **Backend:** Python, FastAPI
*   **AI/Agents:** `google-adk`
*   **Database:** PostgreSQL (Supabase)
*   **Real-time Communication:** WebSockets
*   **Deployment:** Docker

**Architecture:**

The system uses a main "Orchestrator" agent that delegates tasks to sub-agents specializing in areas like:

*   Vendor Management
*   Budget and Expenses
*   Rituals and Cultural Aspects
*   Creative Elements (e.g., mood boards)
*   Tasks and Timelines

The application uses a "Smart Context System" to manage the context for the LLM, ensuring that the AI has the relevant information for the conversation.

## Building and Running

**Important:** The `sanskara` directory should be considered the root directory for all commands.

### 1. Prerequisites

*   Python 3.11+
*   Docker (optional)
*   A Supabase project

### 2. Environment Setup

1.  Create a `.env` file in the `sanskara` directory. You can use `.env.example` as a template.
2.  Fill in the required environment variables, including your Supabase credentials and Google API key.

### 3. Database Setup

The Supabase database for this project is running remotely. If you need to make any changes to the database schema, please do so directly in the Supabase dashboard.

1.  In your Supabase project, enable the `pgvector` extension.
2.  Execute the SQL script located at `docs/design/overall_schema.sql` in the Supabase SQL editor to set up the database schema.

### 4. Installation

From the `SanskaraAI` directory, install the required Python dependencies:

```bash
pip install -r sanskara/requirements.txt
```

### 5. Running the Application

1.  Navigate to the `sanskara` directory:
    ```bash
    cd sanskara
    ```
2.  Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```
3.  Run the application:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8765 --reload
    ```

The application will be available at `http://localhost:8765`.

### 6. Running with Docker

To run the application using Docker from the `SanskaraAI` directory:

```bash
docker-compose up --build
```

## Development Conventions

*   **Code Style:** This project uses `black` for code formatting and `flake8` for linting.
*   **Testing:** Tests are written using `pytest`. To run the tests, navigate to the `sanskara` directory and run:
    ```bash
    pytest -q
    ```
*   **Commit Messages:** Please follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.