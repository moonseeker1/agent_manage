"""
Agent Executor - 执行不同类型的 Agent

支持的 Agent 类型:
- openai: OpenAI GPT 模型
- anthropic: Anthropic Claude 模型
- mcp: MCP Server
- custom: 自定义 Webhook
- cli: 命令行工具
"""

import asyncio
import os
import httpx
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    """Agent 执行器基类"""

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent 并返回结果"""
        pass


class OpenAIExecutor(BaseExecutor):
    """OpenAI GPT 执行器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.model = config.get("model", "gpt-4-turbo-preview")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.system_prompt = config.get("system_prompt", "")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 OpenAI API 调用"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        user_message = input_data.get("message", "")
        if isinstance(input_data, dict) and "prompt" in input_data:
            user_message = input_data["prompt"]

        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        return {
            "response": response.choices[0].message.content,
            "model": self.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }


class AnthropicExecutor(BaseExecutor):
    """Anthropic Claude 执行器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
        self.system_prompt = config.get("system_prompt", "")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Anthropic API 调用"""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)

        user_message = input_data.get("message", "")
        if isinstance(input_data, dict) and "prompt" in input_data:
            user_message = input_data["prompt"]

        response = await client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        # 提取文本内容
        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        return {
            "response": text_content,
            "model": self.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }


class MCPExecutor(BaseExecutor):
    """MCP Server 执行器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.server_url = config.get("server_url")
        self.server_command = config.get("server_command")
        self.tools = config.get("tools", [])
        self.timeout = config.get("timeout", 300)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 MCP Server 调用"""
        # 如果配置了 HTTP URL，使用 HTTP 调用
        if self.server_url:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/execute",
                    json={"input": input_data},
                    timeout=self.timeout
                )
                return response.json()

        # 如果配置了命令，使用进程调用
        if self.server_command:
            process = await asyncio.create_subprocess_shell(
                self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            import json
            stdin_data = json.dumps(input_data).encode()

            stdout, stderr = await asyncio.wait_for(
                process.communicate(stdin_data),
                timeout=self.timeout
            )

            if process.returncode != 0:
                return {
                    "error": stderr.decode(),
                    "return_code": process.returncode
                }

            return json.loads(stdout.decode())

        return {"error": "No server_url or server_command configured"}


class WebhookExecutor(BaseExecutor):
    """自定义 Webhook 执行器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.webhook_url = config.get("webhook_url")
        self.method = config.get("method", "POST")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 300)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Webhook 调用"""
        async with httpx.AsyncClient() as client:
            if self.method.upper() == "POST":
                response = await client.post(
                    self.webhook_url,
                    json=input_data,
                    headers=self.headers,
                    timeout=self.timeout
                )
            else:
                response = await client.get(
                    self.webhook_url,
                    params=input_data,
                    headers=self.headers,
                    timeout=self.timeout
                )

            try:
                return response.json()
            except:
                return {"response": response.text, "status_code": response.status_code}


class CLIExecutor(BaseExecutor):
    """命令行执行器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.command = config.get("command")
        self.args = config.get("args", [])
        self.timeout = config.get("timeout", 300)
        self.env = config.get("env", {})

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 CLI 命令"""
        import json

        # 准备输入
        input_text = input_data.get("message", "")
        if isinstance(input_data, dict):
            input_text = json.dumps(input_data)

        # 合并环境变量
        env = {**os.environ, **self.env}

        # 执行命令
        process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input_text.encode()),
                timeout=self.timeout
            )

            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "return_code": process.returncode
            }
        except asyncio.TimeoutError:
            process.kill()
            return {"error": f"Command timed out after {self.timeout} seconds"}


def get_executor(agent_type: str, config: Dict[str, Any]) -> BaseExecutor:
    """根据 Agent 类型获取对应的执行器"""
    executors = {
        "openai": OpenAIExecutor,
        "anthropic": AnthropicExecutor,
        "claude": AnthropicExecutor,  # Claude 使用 Anthropic 执行器
        "mcp": MCPExecutor,
        "custom": WebhookExecutor,
        "webhook": WebhookExecutor,
        "cli": CLIExecutor,
    }

    executor_class = executors.get(agent_type)
    if not executor_class:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return executor_class(config)
