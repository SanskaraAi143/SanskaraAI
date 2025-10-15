# API Endpoints Reference

This document provides a reference for the RESTful API endpoints exposed by the Sanskara AI backend. These endpoints facilitate communication between the frontend application and the backend services, enabling various functionalities related to wedding planning, user management, and agent interactions.

## Base URL

The base URL for all API endpoints is typically `http://localhost:8000` in a local development environment, or the deployed domain in production.

## Authentication

All protected endpoints require authentication. The specific authentication mechanism (e.g., JWT in the `Authorization` header) is handled by the FastAPI application.

## Endpoints

### 1. Health Check

*   **Path**: `/health`
*   **Method**: `GET`
*   **Description**: Provides a comprehensive overview of the application's operational status and its critical dependencies.
*   **Reference**: See `sanskara/docs/health_endpoint.md` for detailed response structure and examples.

### 2. Onboarding

These endpoints are used for user and partner onboarding processes.

#### 2.1. Submit Onboarding Data

*   **Path**: `/onboarding/submit`
*   **Method**: `POST`
*   **Description**: Submits initial onboarding data for a new user or partner.
*   **Request Body**: (Example - actual schema may vary based on `sanskara/api/onboarding/` implementation)
    ```json
    {
        "email": "user@example.com",
        "display_name": "John Doe",
        "preferences": {
            "wedding_style": "modern"
        }
    }
    ```
*   **Response**: (Example)
    ```json
    {
        "message": "Onboarding data submitted successfully",
        "user_id": "uuid-of-new-user"
    }
    ```

#### 2.2. Get Partner Details

*   **Path**: `/onboarding/partner-details`
*   **Method**: `GET`
*   **Description**: Retrieves details for a partner based on their email.
*   **Query Parameters**: `email` (string, required)
*   **Response**: (Example)
    ```json
    {
        "email": "partner@example.com",
        "display_name": "Jane Smith",
        "status": "onboarded"
    }
    ```

### 3. Weddings

These endpoints manage wedding-related information.

#### 3.1. Get Wedding Details

*   **Path**: `/weddings/{weddingId}`
*   **Method**: `GET`
*   **Description**: Retrieves comprehensive details for a specific wedding.
*   **Path Parameters**: `weddingId` (string, UUID of the wedding)
*   **Response**: (Example - actual schema may vary based on `sanskara/api/weddings/` implementation and `sanskara/models.py`)
    ```json
    {
        "wedding_id": "uuid-of-wedding",
        "wedding_name": "John & Jane's Wedding",
        "wedding_date": "2025-10-26",
        "location": "Venue Name",
        "status": "planning",
        "members": [
            { "user_id": "uuid", "role": "bride" }
        ]
    }
    ```

#### 3.2. Update Wedding Details

*   **Path**: `/weddings/{weddingId}`
*   **Method**: `PUT` or `PATCH`
*   **Description**: Updates existing details for a specific wedding.
*   **Path Parameters**: `weddingId` (string, UUID of the wedding)
*   **Request Body**: (Partial or full wedding object, depending on PUT/PATCH)
    ```json
    {
        "wedding_name": "John & Jane's Dream Wedding",
        "status": "active"
    }
    ```
*   **Response**: (Example)
    ```json
    {
        "message": "Wedding updated successfully",
        "wedding_id": "uuid-of-wedding"
    }
    ```

### 4. Chat Messages

These endpoints handle chat message history.

#### 4.1. Get Chat Messages for a Session

*   **Path**: `/weddings/{wedding_id}/sessions/{adk_session_id}/messages`
*   **Method**: `GET`
*   **Description**: Retrieves chat messages for a specific ADK session within a wedding.
*   **Path Parameters**: `wedding_id` (string), `adk_session_id` (string)
*   **Query Parameters**: `limit` (integer, optional), `offset` (integer, optional)
*   **Response**: (Example - actual schema may vary based on `sanskara/api/history/` implementation and `sanskara/models.py`)
    ```json
    [
        {
            "message_id": "uuid",
            "sender_type": "user",
            "sender_name": "John",
            "content": "Hi, I need help with vendors.",
            "timestamp": "2025-10-11T10:00:00Z"
        },
        {
            "message_id": "uuid",
            "sender_type": "ai",
            "sender_name": "Sanskara AI",
            "content": "Certainly! What kind of vendors are you looking for?",
            "timestamp": "2025-10-11T10:00:05Z"
        }
    ]
    ```

### 5. Artifacts

These endpoints manage wedding-related artifacts (documents, images, etc.).

#### 5.1. Upload Artifact

*   **Path**: `/artifacts/upload`
*   **Method**: `POST`
*   **Description**: Uploads a new artifact related to a wedding.
*   **Request Body**: `multipart/form-data` (file upload)
*   **Response**: (Example)
    ```json
    {
        "message": "Artifact uploaded successfully",
        "artifact_id": "uuid-of-artifact",
        "file_name": "contract.pdf"
    }
    ```

#### 5.2. List Artifacts

*   **Path**: `/artifacts/list`
*   **Method**: `GET`
*   **Description**: Lists all artifacts for a given wedding or user.
*   **Query Parameters**: `wedding_id` (string, optional), `user_id` (string, optional), `category` (string, optional)
*   **Response**: (Example)
    ```json
    [
        {
            "artifact_id": "uuid",
            "file_name": "venue_contract.pdf",
            "category": "contracts",
            "upload_date": "2025-09-01",
            "url": "/artifacts/content/uuid"
        }
    ]
    ```

#### 5.3. Get Artifact Content

*   **Path**: `/artifacts/content/{artifact_id}`
*   **Method**: `GET`
*   **Description**: Retrieves the content of a specific artifact.
*   **Path Parameters**: `artifact_id` (string, UUID of the artifact)
*   **Response**: File content (e.g., PDF, image, text file).

### 6. Session History

These endpoints provide access to the history of events within a session.

#### 6.1. Get Session Event History

*   **Path**: `/weddings/sessions/{session_id}/history`
*   **Method**: `GET`
*   **Description**: Retrieves a detailed history of events for a specific session.
*   **Path Parameters**: `session_id` (string, UUID of the session)
*   **Query Parameters**: `limit` (integer, optional), `offset` (integer, optional), `event_type` (string, optional)
*   **Response**: (Example - actual schema may vary based on `sanskara/api/history/` implementation)
    ```json
    [
        {
            "event_id": "uuid",
            "event_type": "task_created",
            "timestamp": "2025-10-11T09:30:00Z",
            "details": {
                "task_id": "uuid-of-task",
                "task_name": "Book Venue"
            }
        },
        {
            "event_id": "uuid",
            "event_type": "message_sent",
            "timestamp": "2025-10-11T10:00:00Z",
            "details": {
                "sender": "user",
                "content": "Looking for florists."
            }
        }
    ]
    ```

### 7. Vendor Onboarding (WebSocket)

*   **Path**: `/vendor_onboarding/onboard`
*   **Method**: `WEBSOCKET`
*   **Description**: Establishes a real-time WebSocket connection for interactive vendor onboarding. This allows for bidirectional communication, enabling the backend to send prompts and receive vendor responses in real-time.
*   **Communication Protocol**: JSON messages over WebSocket.
*   **Reference**: See `sanskara/agent_websocket/service.py` for implementation details.

