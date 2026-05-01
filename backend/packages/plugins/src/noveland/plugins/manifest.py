import re
from typing import Any

from noveland.plugins.categories import PluginCategory
from pydantic import BaseModel, ConfigDict, Field, field_validator

IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


class PluginManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: str = Field(min_length=1)
    category: PluginCategory
    version: str = Field(min_length=1)
    config_schema: dict[str, Any]
    capabilities: tuple[str, ...] = Field(min_length=1)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError(
                "identifier must use lowercase slug or dotted form, "
                "for example 'builtin.openai_compatible' or 'local-memory'"
            )
        return value

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        invalid = [capability for capability in value if not capability.strip()]
        if invalid:
            raise ValueError("capabilities must not contain empty values")
        return value
