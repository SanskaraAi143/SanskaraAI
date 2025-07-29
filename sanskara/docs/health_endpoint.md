# Health Endpoint

This document describes the `/health` endpoint, which provides a comprehensive overview of the application's operational status and its critical dependencies.

## Purpose

The health endpoint is designed for monitoring and alerting systems to quickly assess the application's health. It provides insights into the connectivity and availability of various internal and external services that the application relies upon.

## Endpoint Details

*   **Path**: `/health`
*   **Method**: `GET`
*   **Response Type**: `application/json`

## Response Structure

The endpoint returns a JSON object with the following structure:

```json
{
    "status": "ok" | "degraded" | "unavailable",
    "checks": {
        "component_name_1": {
            "status": "ok" | "degraded" | "unavailable",
            "message": "Descriptive message about the component's status"
        },
        "component_name_2": {
            "status": "ok" | "degraded" | "unavailable",
            "message": "Descriptive message about the component's status"
        },
        // ... more components
    }
}
```

### Fields

*   `status` (string): The overall health status of the application.
    *   `"ok"`: All critical components are operating normally.
    *   `"degraded"`: One or more non-critical components are experiencing issues, or critical components are partially functional.
    *   `"unavailable"`: One or more critical components are completely non-functional, rendering the application unable to perform its primary functions.
*   `checks` (object): An object containing the status of individual components. Each key represents a component, and its value is an object with `status` and `message` fields for that component.

## Component Checks

The `/health` endpoint currently includes checks for the following components:

*   **`application`**: Basic check to confirm the FastAPI application is running.
*   **`astra_db`**: Verifies connectivity to the AstraDB database.
*   **`local_db`**: Checks the connection to the local SQLite session database.
*   **`agentops`**: Assesses the reachability and configuration of the AgentOps API.
*   **`supabase`**: Confirms connectivity to the Supabase database and verifies the initialization and availability of its MCP toolset and `execute_sql` tool.

## Example Responses

### Healthy Response

```json
{
    "status": "ok",
    "checks": {
        "application": {
            "status": "ok",
            "message": "Application is running"
        },
        "astra_db": {
            "status": "ok",
            "message": "AstraDB connection successful"
        },
        "local_db": {
            "status": "ok",
            "message": "Local session database connection successful"
        },
        "agentops": {
            "status": "ok",
            "message": "AgentOps API key is configured"
        },
        "supabase": {
            "status": "ok",
            "message": "Supabase database and MCP toolset available"
        }
    }
}
```

### Degraded Response (Example: AgentOps API key not found, Supabase MCP not available)

```json
{
    "status": "degraded",
    "checks": {
        "application": {
            "status": "ok",
            "message": "Application is running"
        },
        "astra_db": {
            "status": "ok",
            "message": "AstraDB connection successful"
        },
        "local_db": {
            "status": "ok",
            "message": "Local session database connection successful"
        },
        "agentops": {
            "status": "degraded",
            "message": "AgentOps API key not found"
        },
        "supabase": {
            "status": "degraded",
            "message": "Supabase MCP toolset or execute_sql tool not available"
        }
    }
}
```

### Unavailable Response (Example: AstraDB connection failed)

```json
{
    "status": "unavailable",
    "checks": {
        "application": {
            "status": "ok",
            "message": "Application is running"
        },
        "astra_db": {
            "status": "unavailable",
            "message": "AstraDB connection failed: Server error '503 Service Unavailable'..."
        },
        "local_db": {
            "status": "ok",
            "message": "Local session database connection successful"
        },
        "agentops": {
            "status": "ok",
            "message": "AgentOps API key is configured"
        },
        "supabase": {
            "status": "ok",
            "message": "Supabase database and MCP toolset available"
        }
    }
}