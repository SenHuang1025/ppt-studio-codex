from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas import LLMProvider, SettingsResponse

API_KEY_HEADER = "x-ppt-studio-api-key"


class LLMConfigurationError(RuntimeError):
    """Raised when the agent LLM runtime cannot be configured safely."""


class MissingAPIKeyError(LLMConfigurationError):
    """Raised when the request does not provide an API key."""


class UnsupportedLLMProviderError(LLMConfigurationError):
    """Raised when the configured provider is not supported by the current runtime."""


class LLMInvocationError(RuntimeError):
    """Raised when a model invocation returns an unusable response."""


class SettingsReader(Protocol):
    async def get_settings(self) -> SettingsResponse: ...


@dataclass(slots=True)
class LLMRuntimeConfig:
    provider: LLMProvider
    model_name: str
    api_base_url: str
    api_key: str
    deliberation_enabled: bool


@dataclass(slots=True)
class LLMRuntime:
    config: LLMRuntimeConfig
    settings: SettingsResponse
    chat_model: Any


async def build_llm_runtime(*, settings_service: SettingsReader, api_key: str) -> LLMRuntime:
    normalized_api_key = api_key.strip()
    if not normalized_api_key:
        raise MissingAPIKeyError("请先在设置页配置 API Key。")

    settings = await settings_service.get_settings()
    runtime_config = LLMRuntimeConfig(
        provider=settings.llm_provider,
        model_name=settings.model_name,
        api_base_url=settings.api_base_url,
        api_key=normalized_api_key,
        deliberation_enabled=settings.multi_agent_deliberation_enabled,
    )
    return LLMRuntime(
        config=runtime_config,
        settings=settings,
        chat_model=create_chat_model(runtime_config),
    )


def create_chat_model(config: LLMRuntimeConfig) -> Any:
    if config.provider in {LLMProvider.OPENAI, LLMProvider.OPENAI_COMPATIBLE}:
        return _create_openai_chat_model(config)
    if config.provider == LLMProvider.ANTHROPIC:
        return _create_anthropic_chat_model(config)
    raise UnsupportedLLMProviderError(f"Unsupported LLM provider: {config.provider!s}")


def _create_openai_chat_model(config: LLMRuntimeConfig) -> Any:
    from langchain_openai import ChatOpenAI

    model_kwargs: dict[str, Any] = {
        "api_key": config.api_key,
        "max_retries": 1,
        "model": config.model_name,
        "temperature": 0.2,
    }
    if config.api_base_url.strip():
        model_kwargs["base_url"] = config.api_base_url.strip()

    return ChatOpenAI(**model_kwargs)


def _create_anthropic_chat_model(config: LLMRuntimeConfig) -> Any:
    from langchain_anthropic import ChatAnthropic

    model_kwargs: dict[str, Any] = {
        "api_key": config.api_key,
        "max_retries": 1,
        "model": config.model_name,
        "temperature": 0.2,
    }
    if config.api_base_url.strip():
        model_kwargs["base_url"] = config.api_base_url.strip()

    return ChatAnthropic(**model_kwargs)


async def invoke_model_text(model: Any, messages: Any) -> str:
    if hasattr(model, "ainvoke"):
        response = await model.ainvoke(messages)
    elif hasattr(model, "invoke"):
        response = await asyncio.to_thread(model.invoke, messages)
    else:
        raise LLMInvocationError("Configured model does not expose invoke/ainvoke.")

    text = extract_text_content(response)
    if not text:
        raise LLMInvocationError("Model returned an empty response.")

    return text


def extract_text_content(response: Any) -> str:
    if isinstance(response, str):
        return response.strip()

    if isinstance(response, dict) and isinstance(response.get("content"), str):
        return response["content"].strip()

    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                text_parts.append(item.strip())
                continue

            if isinstance(item, dict):
                maybe_text = item.get("text")
                if isinstance(maybe_text, str) and maybe_text.strip():
                    text_parts.append(maybe_text.strip())

        return "\n".join(text_parts).strip()

    return ""


def extract_json_payload(raw_text: str) -> Any:
    normalized_text = raw_text.strip()
    if not normalized_text:
        raise ValueError("No JSON payload found in model response.")

    fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", normalized_text, flags=re.DOTALL)
    if fenced_match:
        normalized_text = fenced_match.group(1).strip()

    try:
        return json.loads(normalized_text)
    except json.JSONDecodeError:
        pass

    object_match = re.search(r"(\{.*\}|\[.*\])", normalized_text, flags=re.DOTALL)
    if not object_match:
        raise ValueError("No JSON object found in model response.")

    return json.loads(object_match.group(1))
