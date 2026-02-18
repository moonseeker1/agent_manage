import asyncio
import json
from typing import Optional, Any
from datetime import datetime
from loguru import logger

from app.core.database import async_session
from app.services.execution_service import ExecutionService
from app.models.execution import ExecutionStatus


class BaseExecutor:
    """Base class for agent executors"""

    async def execute(self, config: dict, input_data: dict) -> dict:
        raise NotImplementedError


class OpenAIExecutor(BaseExecutor):
    """Executor for OpenAI API agents"""

    def __init__(self, config: dict):
        self.config = config
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-4-turbo-preview")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.system_prompt = config.get("system_prompt", "You are a helpful assistant.")

    async def execute(self, config: dict, input_data: dict) -> dict:
        """Execute using OpenAI API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            messages = [
                {"role": "system", "content": self.system_prompt}
            ]

            # Add input data as user message
            if input_data:
                user_message = input_data.get("message", json.dumps(input_data))
                messages.append({"role": "user", "content": user_message})

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            return {
                "success": True,
                "response": response.choices[0].message.content,
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"OpenAI execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class MCPExecutor(BaseExecutor):
    """Executor for MCP Server agents"""

    def __init__(self, config: dict):
        self.config = config
        self.server_url = config.get("server_url")
        self.server_command = config.get("server_command")
        self.tools = config.get("tools", [])

    async def execute(self, config: dict, input_data: dict) -> dict:
        """Execute using MCP Server"""
        try:
            # MCP implementation would go here
            # For now, return a placeholder response
            logger.info(f"MCP execution with config: {config}, input: {input_data}")

            return {
                "success": True,
                "response": f"MCP execution completed for server: {self.server_url or self.server_command}",
                "tools_used": self.tools
            }

        except Exception as e:
            logger.error(f"MCP execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class CustomExecutor(BaseExecutor):
    """Executor for custom agents"""

    def __init__(self, config: dict):
        self.config = config
        self.webhook_url = config.get("webhook_url")
        self.custom_code = config.get("custom_code")

    async def execute(self, config: dict, input_data: dict) -> dict:
        """Execute custom agent logic"""
        try:
            import httpx

            # If webhook URL is provided, call it
            if self.webhook_url:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.webhook_url,
                        json={"config": config, "input": input_data},
                        timeout=60.0
                    )
                    response.raise_for_status()
                    return {
                        "success": True,
                        "response": response.json()
                    }

            # If custom code is provided, execute it
            if self.custom_code:
                # Create execution context
                context = {
                    "config": config,
                    "input": input_data,
                    "result": None
                }
                exec(self.custom_code, context)
                return {
                    "success": True,
                    "response": context.get("result")
                }

            return {
                "success": True,
                "response": "Custom execution completed (no action specified)"
            }

        except Exception as e:
            logger.error(f"Custom execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_executor(agent_type: str, config: dict) -> BaseExecutor:
    """Get the appropriate executor based on agent type"""
    executors = {
        "openai": OpenAIExecutor,
        "mcp": MCPExecutor,
        "custom": CustomExecutor
    }

    executor_class = executors.get(agent_type, CustomExecutor)
    return executor_class(config)


async def execute_agent_task(execution_id: str, agent_id: str, input_data: Optional[dict] = None):
    """Background task to execute a single agent"""
    from uuid import UUID
    from app.services.agent_service import AgentService

    async with async_session() as db:
        execution_service = ExecutionService(db)
        agent_service = AgentService(db)

        try:
            # Update status to running
            await execution_service.start_execution(UUID(execution_id))
            await execution_service.add_log(
                UUID(execution_id),
                "info",
                f"Starting execution for agent {agent_id}"
            )

            # Get agent
            agent = await agent_service.get_agent(UUID(agent_id))
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Get executor
            executor = get_executor(agent.agent_type, agent.config)

            # Execute
            start_time = datetime.utcnow()
            result = await executor.execute(agent.config, input_data or {})
            end_time = datetime.utcnow()

            # Log result
            await execution_service.add_log(
                UUID(execution_id),
                "info" if result.get("success") else "error",
                f"Execution completed: {json.dumps(result)[:500]}"
            )

            # Add metrics
            duration = (end_time - start_time).total_seconds()
            await execution_service.add_metric(
                "execution_duration",
                duration,
                agent_id=UUID(agent_id),
                execution_id=UUID(execution_id),
                unit="seconds"
            )

            if result.get("usage", {}).get("total_tokens"):
                await execution_service.add_metric(
                    "tokens_used",
                    result["usage"]["total_tokens"],
                    agent_id=UUID(agent_id),
                    execution_id=UUID(execution_id),
                    unit="tokens"
                )

            # Update execution status
            if result.get("success"):
                await execution_service.complete_execution(
                    UUID(execution_id),
                    output_data=result
                )
            else:
                await execution_service.complete_execution(
                    UUID(execution_id),
                    error_message=result.get("error", "Unknown error")
                )

        except Exception as e:
            logger.exception(f"Execution failed: {e}")
            await execution_service.add_log(
                UUID(execution_id),
                "error",
                f"Execution failed: {str(e)}"
            )
            await execution_service.complete_execution(
                UUID(execution_id),
                error_message=str(e)
            )


async def execute_group_task(execution_id: str, group_id: str, input_data: Optional[dict] = None):
    """Background task to execute an agent group"""
    from uuid import UUID
    from app.services.agent_service import AgentGroupService

    async with async_session() as db:
        execution_service = ExecutionService(db)
        group_service = AgentGroupService(db)

        try:
            # Update status to running
            await execution_service.start_execution(UUID(execution_id))
            await execution_service.add_log(
                UUID(execution_id),
                "info",
                f"Starting group execution for group {group_id}"
            )

            # Get group
            group = await group_service.get_group(UUID(group_id))
            if not group:
                raise ValueError(f"Group {group_id} not found")

            # Sort members by priority
            members = sorted(group.members, key=lambda m: m.priority)

            results = []
            current_input = input_data

            # Execute based on mode
            if group.execution_mode == "parallel":
                # Execute all agents in parallel
                tasks = []
                for member in members:
                    executor = get_executor(member.agent.agent_type, member.agent.config)
                    tasks.append(executor.execute(member.agent.config, current_input))

                results = await asyncio.gather(*tasks, return_exceptions=True)
                results = [
                    {"agent_id": str(m.agent_id), "result": r if not isinstance(r, Exception) else {"success": False, "error": str(r)}}
                    for m, r in zip(members, results)
                ]

            else:  # sequential
                # Execute agents one by one, passing output to next
                for member in members:
                    await execution_service.add_log(
                        UUID(execution_id),
                        "info",
                        f"Executing agent {member.agent.name}"
                    )

                    executor = get_executor(member.agent.agent_type, member.agent.config)
                    result = await executor.execute(member.agent.config, current_input)
                    results.append({
                        "agent_id": str(member.agent_id),
                        "agent_name": member.agent.name,
                        "result": result
                    })

                    # Pass output to next agent
                    if result.get("success") and result.get("response"):
                        current_input = {"message": result["response"]} if isinstance(result["response"], str) else result["response"]

            # Complete execution
            await execution_service.add_log(
                UUID(execution_id),
                "info",
                f"Group execution completed with {len(results)} agent executions"
            )

            await execution_service.complete_execution(
                UUID(execution_id),
                output_data={"results": results}
            )

        except Exception as e:
            logger.exception(f"Group execution failed: {e}")
            await execution_service.add_log(
                UUID(execution_id),
                "error",
                f"Group execution failed: {str(e)}"
            )
            await execution_service.complete_execution(
                UUID(execution_id),
                error_message=str(e)
            )
