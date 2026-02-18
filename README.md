# Agent Management System

A comprehensive system for managing and monitoring AI agents, supporting MCP Server, OpenAI API, and custom agents.

## Features

- **Agent Management**: Create, configure, and manage different types of agents
- **Agent Groups**: Group agents for sequential or parallel execution
- **Execution Monitoring**: Real-time monitoring of agent executions
- **Metrics & Analytics**: Track performance metrics and execution history
- **WebSocket Support**: Real-time updates for execution status and logs

## Tech Stack

### Frontend
- React 18 + TypeScript
- Ant Design 5
- Vite
- Zustand (state management)
- React Router

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Redis

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/moonseeker1/agent_manage.git
cd agent_manage

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

#### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the server
uvicorn app.main:app --reload
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## Project Structure

```
.
├── frontend/                # React frontend
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   ├── services/       # API and WebSocket services
│   │   ├── stores/         # State management
│   │   └── types/          # TypeScript types
│   └── package.json
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   ├── schemas/        # Pydantic schemas
│   │   └── core/           # Configuration
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

## API Endpoints

### Agents
- `GET /api/agents` - List agents
- `POST /api/agents` - Create agent
- `GET /api/agents/{id}` - Get agent details
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent
- `POST /api/agents/{id}/enable` - Enable agent
- `POST /api/agents/{id}/disable` - Disable agent

### Groups
- `GET /api/groups` - List groups
- `POST /api/groups` - Create group
- `GET /api/groups/{id}` - Get group details
- `PUT /api/groups/{id}` - Update group
- `DELETE /api/groups/{id}` - Delete group

### Executions
- `GET /api/executions` - List executions
- `GET /api/executions/{id}` - Get execution details
- `GET /api/executions/{id}/logs` - Get execution logs
- `POST /api/executions/agents/{id}/execute` - Execute agent
- `POST /api/executions/groups/{id}/execute` - Execute group
- `POST /api/executions/{id}/cancel` - Cancel execution

### Metrics
- `GET /api/metrics/executions` - Get execution metrics
- `GET /api/metrics/agents` - Get all agent metrics
- `GET /api/metrics/agents/{id}` - Get agent metrics

### WebSocket
- `WS /ws` - Global updates
- `WS /ws/executions/{id}` - Execution-specific updates

## Agent Types

### OpenAI
```json
{
  "api_key": "your-api-key",
  "model": "gpt-4-turbo-preview",
  "temperature": 0.7,
  "max_tokens": 2000,
  "system_prompt": "You are a helpful assistant."
}
```

### MCP Server
```json
{
  "server_url": "http://localhost:3001",
  "server_command": "node server.js",
  "tools": ["tool1", "tool2"]
}
```

### Custom
```json
{
  "webhook_url": "https://your-webhook.com/execute",
  "custom_code": "// JavaScript code to execute"
}
```

## License

MIT License
