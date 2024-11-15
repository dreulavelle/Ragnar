from typing import Optional

import requests
from pydantic import BaseModel, Field, field_validator


class RagnarException(Exception):
    """Generic Exception for Ragnar"""


class OllamaOptions(BaseModel):
    """Handle Ollama Options"""
    num_keep: int = 5
    seed: int = 42
    num_predict: int = 100
    top_k: int = 20
    top_p: float = 0.9
    min_p: float = 0.0
    tfs_z: float = 0.5
    typical_p: float = 0.7
    repeat_last_n: int = 33
    temperature: float = 0.8
    repeat_penalty: float = 1.2
    presence_penalty: float = 1.5
    frequency_penalty: float = 1.0
    mirostat: int = 1
    mirostat_tau: float = 0.8
    mirostat_eta: float = 0.6
    penalize_newline: bool = True
    stop: list = ["\n", "user:"]
    numa: bool = False
    num_ctx: int = 1024
    num_batch: int = 2
    num_gpu: int = 1
    main_gpu: int = 0
    low_vram: bool = False
    f16_kv: bool = True
    vocab_only: bool = False
    use_mmap: bool = True
    use_mlock: bool = False
    num_thread: int = 8

    def to_dict(self) -> dict:
        """Convert OllamaOptions to a dictionary"""
        return self.model_dump(mode="json")


class OllamaModel(BaseModel):
    """Handle Ollama Settings"""
    api_url: str = "http://localhost:11434"  # Ollama is bundled with Ragnar
    model: str = "llama3.2"
    temperature: float = 0.8
    max_tokens: int = 32000
    stream: bool = False
    options: OllamaOptions = OllamaOptions()

    @field_validator("api_url", mode="before")
    def validate_api_url(cls, v):
        if not v.startswith("http://"):
            v = f"http://{v}"
        ping = requests.get(v).text
        if "Ollama is running" not in ping:
            raise RagnarException("Ollama is not running")
        return v


class DiscordModel(BaseModel):
    """Handle Discord Settings"""
    token: str = Field(default="")
    bot_invite_url: Optional[str] = Field(default="")


class ExternalTokens(BaseModel):
    """Handle External Tokens"""
    bfl_api_key: str = ""
    huggingface_token: str = ""


class AppSettings(BaseModel):
    """Handles Ragnar Application Settings"""
    version: str = "0.1.0"
    debug: bool = True
    log: bool = True
    discord: DiscordModel = DiscordModel()
    external_tokens: ExternalTokens = ExternalTokens()
    ollama: OllamaModel = OllamaModel()
