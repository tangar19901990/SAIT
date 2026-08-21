from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RuntimeConfig:
    provider: str = os.getenv("AI_PROVIDER", "openai")
    model: str = os.getenv("AI_MODEL", "")
    api_key: str = os.getenv("AI_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)
