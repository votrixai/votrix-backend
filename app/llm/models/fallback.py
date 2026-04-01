"""Primary → backup model invocation with automatic retry on failure."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


async def invoke_with_fallback(
    model: BaseChatModel,
    messages: list[BaseMessage],
    backup_model_name: str | None = None,
    tools: list | None = None,
    config: dict | None = None,
) -> BaseMessage:
    """Invoke the primary model; on failure, retry with backup.

    Steps:
    1. Try model.ainvoke(messages, config=config)
    2. On exception:
       a. If no backup_model_name → re-raise
       b. Log warning, get backup via get_model()
       c. Bind tools if present, retry
       d. On backup failure → log error, re-raise
    """
    try:
        return await model.ainvoke(messages, config=config)
    except Exception as primary_error:
        if not backup_model_name:
            raise

        logger.warning(
            f"Primary model failed ({type(primary_error).__name__}: {primary_error}), "
            f"retrying with backup model '{backup_model_name}'"
        )

        from app.llm.models.resolver import get_model

        backup = get_model(backup_model_name)
        if tools:
            backup = backup.bind_tools(tools)

        try:
            return await backup.ainvoke(messages, config=config)
        except Exception as backup_error:
            logger.error(
                f"Backup model '{backup_model_name}' also failed: "
                f"{type(backup_error).__name__}: {backup_error}"
            )
            raise
