from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/templates", tags=["Templates"])


# Predefined agent templates
AGENT_TEMPLATES = {
    "openai_assistant": {
        "name": "OpenAI Assistant",
        "description": "A general-purpose OpenAI assistant",
        "agent_type": "openai",
        "config": {
            "model": "gpt-4-turbo-preview",
            "temperature": 0.7,
            "max_tokens": 2000,
            "system_prompt": "You are a helpful AI assistant."
        }
    },
    "openai_coder": {
        "name": "Code Assistant",
        "description": "An OpenAI assistant specialized in coding",
        "agent_type": "openai",
        "config": {
            "model": "gpt-4-turbo-preview",
            "temperature": 0.3,
            "max_tokens": 4000,
            "system_prompt": "You are an expert programmer. Help users with coding tasks, debugging, and software development best practices."
        }
    },
    "openai_writer": {
        "name": "Content Writer",
        "description": "An OpenAI assistant for content writing",
        "agent_type": "openai",
        "config": {
            "model": "gpt-4-turbo-preview",
            "temperature": 0.8,
            "max_tokens": 3000,
            "system_prompt": "You are a skilled content writer. Help users create engaging and well-structured content."
        }
    },
    "mcp_filesystem": {
        "name": "MCP Filesystem",
        "description": "MCP server for filesystem operations",
        "agent_type": "mcp",
        "config": {
            "server_command": "mcp-server-filesystem",
            "tools": ["read_file", "write_file", "list_directory", "create_directory"]
        }
    },
    "mcp_github": {
        "name": "MCP GitHub",
        "description": "MCP server for GitHub operations",
        "agent_type": "mcp",
        "config": {
            "server_command": "mcp-server-github",
            "tools": ["create_issue", "create_pr", "list_repos", "search_code"]
        }
    },
    "custom_webhook": {
        "name": "Custom Webhook Agent",
        "description": "A custom agent that calls a webhook",
        "agent_type": "custom",
        "config": {
            "webhook_url": "https://your-webhook.com/execute",
            "timeout": 60
        }
    }
}


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    agent_type: str
    config: dict


class TemplatesListResponse(BaseModel):
    templates: List[TemplateResponse]


@router.get("", response_model=TemplatesListResponse)
async def list_templates(
    current_user: User = Depends(get_current_user)
):
    """Get all available agent templates"""
    templates = [
        TemplateResponse(
            id=key,
            name=value["name"],
            description=value["description"],
            agent_type=value["agent_type"],
            config=value["config"]
        )
        for key, value in AGENT_TEMPLATES.items()
    ]
    return TemplatesListResponse(templates=templates)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific template by ID"""
    if template_id not in AGENT_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    template = AGENT_TEMPLATES[template_id]
    return TemplateResponse(
        id=template_id,
        name=template["name"],
        description=template["description"],
        agent_type=template["agent_type"],
        config=template["config"]
    )
