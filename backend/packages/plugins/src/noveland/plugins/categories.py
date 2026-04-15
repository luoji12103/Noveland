from enum import StrEnum


class PluginCategory(StrEnum):
    MODEL_PROVIDER = "model_provider"
    MEMORY_BACKEND = "memory_backend"
    WORLD_RULES = "world_rules"
    PERSONA_POLICY = "persona_policy"
    NARRATIVE_WRITER = "narrative_writer"
