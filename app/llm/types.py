"""Tool types for the LLM layer."""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel, Field, SkipValidation
from typing_extensions import Annotated

from langchain_core.tools import StructuredTool
from langchain_core.tools.base import ArgsSchema


class RecordRule(str, Enum):
    WRITE_ALL = "write_all"
    WRITE_INTERMEDIATE_ONLY = "write_intermediate_only"
    WRITE_NONE = "write_none"


class RecordFormat(str, Enum):
    AI_AND_TOOL = "ai_and_tool"
    TOOL_AS_AI = "tool_as_ai"


class OperationType(str, Enum):
    READ_ONLY = "read_only"
    WRITE = "write"


class ToolStructure(BaseModel):
    name: str
    description: str
    func: Callable
    args_schema: Annotated[ArgsSchema, SkipValidation]
    record_rule: RecordRule = RecordRule.WRITE_INTERMEDIATE_ONLY
    record_format: RecordFormat = RecordFormat.AI_AND_TOOL
    operation_type: OperationType = OperationType.READ_ONLY
    return_direct: bool = False

    def to_structured_tool(self) -> StructuredTool:
        return StructuredTool.from_function(
            func=self.func,
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
        )


class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]
    id: str

    @classmethod
    def from_call(cls, call: Dict[str, Any]) -> "ToolCall":
        return cls(name=call["name"], args=call["args"], id=call["id"])

    def to_call(self) -> Dict[str, Any]:
        return {"name": self.name, "args": self.args, "id": self.id}


class ToolResponse(BaseModel):
    status: bool
    func_name: str
    args: Dict[str, Any]
    message: Optional[str] = None

    def __str__(self) -> str:
        return self.model_dump_json(include={"status", "message"})
