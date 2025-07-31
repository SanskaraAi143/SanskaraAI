# Sanskara AI - Collaborative Wedding Planner

Sanskara AI is an ambitious project aimed at building a comprehensive and reliable AI wedding planner. It is designed to navigate the beautiful complexities of Hindu traditions and the delicate dynamics between two families, offering a collaborative platform for wedding planning.

## Table of Contents

-   [Features](#features)
-   [Technology Stack](#technology-stack)
-   [Getting Started](#getting-started)
    -   [Prerequisites](#prerequisites)
    -   [Environment Variables](#environment-variables)
    -   [Installation and Setup](#installation-and-setup)
-   [Usage](#usage)
-   [Project Structure](#project-structure)
-   [Testing](#testing)
-   [Contributing](#contributing)
-   [License](#license)

## Features

Sanskara AI leverages a multi-agent system architecture to provide intelligent assistance across various aspects of wedding planning:

*   **Orchestrator Agent**: The central brain that manages the primary conversation flow, understands user intent, delegates tasks to specialized agents, synthesizes information, and manages conversational context.
*   **Specialized Agents**:
    *   **Vendor Management Agent**: Handles interactions with vendors, shortlisting, and service management.
    *   **Ritual & Cultural Agent**: Provides information and guidance on Hindu wedding traditions and rituals.
    *   **Guest & Communication Agent**: Manages guest lists and facilitates communications via integrated channels.
    *   **Budget & Expense Agent**: Assists with budget planning and expense tracking.
    *   **Task & Timeline Agent**: Manages tasks and timelines for both users and vendors.
    *   **Creative Agent**: Helps with mood boards and generating creative ideas.
    *   **Collaboration & Consensus Agent**: Facilitates communication and decision-making between the bride and groom's families.
*   **API Endpoints**: Provides RESTful APIs for onboarding and managing wedding details.
*   **Real-time Communication**: Utilizes WebSockets for a responsive, chat-like user experience.
*   **Health Monitoring**: Includes comprehensive health checks for various integrated services like databases and external APIs.

## Technology Stack

The project is built on a modern, scalable, and integrated stack:

*   **Framework**: Google Agent Development Kit (ADK) for building and orchestrating the multi-agent system.
*   **Language**: Python
*   **AI Models**: Google's Gemini models (via Vertex AI) for advanced reasoning and multi-modal capabilities.
*   **Web Framework**: FastAPI for exposing WebSocket and REST endpoints.
*   **Database**: Supabase (PostgreSQL) for primary data storage, including real-time capabilities.
*   **NoSQL Database**: AstraDB (Cassandra-based) for specific data storage needs.
*   **Real-time Communication**: WebSockets.
*   **Caching**: Redis for caching frequent queries and managing session state.
*   **Task Queue**: Celery (with Redis broker) for long-running or asynchronous tasks.
*   **Observability**: AgentOps for monitoring agent behavior.
*   **Environment Management**: Python-dotenv.
*   **Logging**: Loguru for structured logging.
*   **External Integrations**: Google Search API, Twilio (for Guest & Communication Agent).

## Getting Started

Follow these instructions to set up and run the Sanskara AI project locally.

### Prerequisites

*   Python 3.9+
*   Docker and Docker Compose
*   Access to Google Cloud Platform (for Gemini models, Vertex AI)
*   Supabase account and project
*   AstraDB account and database
*   AgentOps account

### Environment Variables

Create a `.env` file in the `sanskara/` directory. Refer to the `sanskara/.env.example` file for a comprehensive list of required environment variables and their descriptions. This file will store your sensitive API keys and configuration details.

### Installation and Setup

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/your-repo/sanskara-ai.git
    cd sanskara-ai
    ```

2.  **Navigate to the `sanskara` directory**:

    ```bash
    cd sanskara
    ```

3.  **Install Python dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Build and run with Docker Compose**:

    Ensure you are in the root directory of the project (where `docker-compose.yml` is located).

    ```bash
    docker-compose up --build
    ```

    This will build the Docker image for the `sanskara` service and start the application.

## Usage

Once the application is running (e.g., via Docker Compose), the FastAPI server will be accessible at `http://localhost:8765`.

*   **API Documentation**: You can access the OpenAPI (Swagger UI) documentation at `http://localhost:8765/docs`.
*   **Health Check**: Check the application's health at `http://localhost:8765/health`.
*   **Onboarding API**: Interact with the onboarding process via `/onboarding` endpoints.
*   **Weddings API**: Manage wedding details via `/weddings` endpoints.
*   **WebSocket**: Connect to the WebSocket endpoint at `ws://localhost:8765/ws` for real-time interactions with the AI agents.

## Project Structure

The core application logic resides in the `sanskara/` directory:

```
sanskara/
├── api/                       # FastAPI application setup and API routes
│   ├── app.py                 # Main FastAPI application instance
│   ├── onboarding/            # Onboarding related models, routes, and services
│   └── weddings/              # Wedding related models and routes
├── agent_websocket/           # WebSocket service implementation
├── docs/                      # Project documentation (health, testing strategy)
├── sanskara/                  # Core AI agent logic and shared components
│   ├── __init__.py
│   ├── agent.py               # Orchestrator Agent definition and sub-agent integration
│   ├── common.py
│   ├── db.py                  # Database connection utilities
│   ├── db_queries.py          # Database query functions
│   ├── helpers.py             # Helper functions (e.g., for Supabase MCP tools)
│   ├── memory/                # Memory service implementation (e.g., Supabase memory)
│   ├── prompt.py              # Prompts for AI agents
│   ├── sub_agents/            # Directory for specialized AI agents
│   │   ├── budget_and_expense_agent/
│   │   ├── creative_agent/
│   │   ├── google_search_agent/
│   │   ├── guest_and_communication_agent/
│   │   ├── ritual_and_cultural_agent/
│   │   ├── setup_agent/
│   │   ├── task_and_timeline_agent/
│   │   └── vendor_management_agent/
│   └── tools.py               # Custom tools available to AI agents (e.g., database interactions)
├── tests/                     # Unit and integration tests
├── Dockerfile                 # Dockerfile for building the application image
├── main.py                    # Application entry point (runs Uvicorn)
├── pyproject.toml             # Poetry configuration
├── requirements.txt           # Python dependencies
├── config.py                  # Application configuration
├── logger.py                  # Custom JSON logger setup
└── README.md                  # This README file
```

## Testing

Tests are located in the `sanskara/tests/` directory. You can run them using `pytest`:

```bash
cd sanskara
pytest
```

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

[Specify your project's license here, e.g., MIT, Apache 2.0, etc.]