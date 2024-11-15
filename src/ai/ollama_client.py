from typing import Any, Dict, Generator, List, Optional, Union

import ollama
from llm_axe import OllamaChat, OnlineAgent, PdfReader
from pydantic import BaseModel

from settings.manager import settings_manager
from utils.logger import logger


class ModelInfo(BaseModel):
    """Model information"""

    name: str
    parameter_size: str
    quantization_level: str
    size: float
    modified_at: str
    digest: str

    def __hash__(self) -> int:
        return hash(self.digest)


class OllamaClient:
    """Ollama API client"""

    def __init__(self):
        self.initialized = False
        self.settings = settings_manager.settings.ollama
        self.available_models = []
        self.running_models = []

        try:
            self.llm_axe = OllamaChat(self.settings.api_url, self.settings.model)
            self.client = ollama.Client(host=self.settings.api_url)
            self.client = self.llm_axe._ollama
            self.online_agent = OnlineAgent(llm=self.llm_axe)
            self.pdf_reader = PdfReader(llm=self.llm_axe)
            self.initialized = True
        except Exception as e:
            logger.exception(f"Failed to initialize Ollama client: {e}")

        available_models = self.llm_axe._ollama.list()
        if available_models:
            for model in available_models["models"]:
                model_info = self._create_model_info(model)
                if model_info not in self.available_models:
                    self.available_models.append(model_info)
                    logger.log("OLLAMA", f"Available model: {model_info.name}")

        running_model = self.list_running_models()
        if (
            running_model
            and running_model != "No models are currently loaded in memory."
        ):
            model_info = self._create_model_info(model)
            if model_info not in self.running_models:
                self.running_models.append(model_info)
                logger.log("OLLAMA", f"Running model: {model_info.name}")
        else:
            logger.warning("No models are currently loaded in memory.")
            if self.available_models:
                logger.debug(
                    f"Loading first available model: {self.available_models[0].name}"
                )
                self.load_model(self.available_models[0].name)
            else:
                logger.debug("No available models, pulling llama3.2")
                self.pull_model("llama3.2")
                self.load_model("llama3.2")
                logger.debug("Loaded llama3.2")

    def _create_model_info(self, model: dict) -> ModelInfo:
        """Create a ModelInfo object from a model dictionary"""
        model_size = model["size"]
        model_size_gb = model_size / (1024**3)
        modified_at_date = model["modified_at"].split("T")[0]

        return ModelInfo(
            name=model["name"],
            parameter_size=model["details"]["parameter_size"],
            quantization_level=model["details"]["quantization_level"],
            size=float(f"{model_size_gb:.2f}"),
            modified_at=modified_at_date,
            digest=model["digest"],
        )

    def validate(self) -> bool:
        """Validate connection to Ollama API"""
        try:
            r = self.session.get(f"{self.settings.api_url}")
            if "Ollama is running" not in r.text:
                raise Exception("Ollama is not running")
            return True
        except Exception as e:
            logger.error(f"Failed to validate Ollama connection: {e}")
            raise

    def chat(
        self,
        messages: list,
        stream: Optional[bool] = None,
        tools: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Send chat messages to Ollama"""
        if not self.initialized:
            raise Exception("Ollama client not initialized")

        logger.log("OLLAMA", "Sending user message to Ollama")

        try:
            if tools:
                # Tools require streaming to be disabled
                response = self.client.chat(
                    model=self.settings.model,
                    messages=messages,
                    tools=tools,
                    stream=False,
                    options={
                        "temperature": self.settings.temperature,
                        "num_ctx": self.settings.num_ctx,
                    },
                )
            else:
                response = self.client.chat(
                    model=self.settings.model,
                    messages=messages,
                    stream=stream if stream is not None else self.settings.stream,
                    options={"temperature": self.settings.temperature},
                )
            return response["message"] if not stream else response
        except ollama.ResponseError as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    def generate(self, prompt: str) -> Dict[str, Any]:
        """Generate a completion from Ollama"""
        try:
            return self.client.generate(model=self.settings.model, prompt=prompt)
        except ollama.ResponseError as e:
            logger.error(f"Ollama generate error: {e}")
            raise

    def create_model(self, name: str, modelfile: str) -> Generator:
        """Create a new model from a Modelfile"""
        return self.client.create(model=name, modelfile=modelfile)

    def show_model(self, name: str) -> Dict[str, Any]:
        """Show information about a model"""
        models = self.list_models()
        if name not in models:
            return f"Model {name} not found"
        return self.client.show(name)

    def copy_model(self, source: str, destination: str) -> None:
        """Copy a model to a new name"""
        logger.log("OLLAMA", f"Copying {source} to {destination}")
        try:
            return self.client.copy(source, destination)
        except ollama.ResponseError as e:
            logger.error(f"Error copying model: {e}")
            return None

    def list_models(self) -> list:
        """List available models"""
        try:
            response = self.client.list()
            return [model["name"] for model in response["models"]]
        except ollama.ResponseError as e:
            logger.error(f"Error listing models: {e}")
            raise

    def pull_model(self, model: str) -> Generator:
        """Pull a model from Ollama"""
        try:
            return self.client.pull(model)
        except ollama.ResponseError as e:
            logger.error(f"Error pulling model: {e}")
            raise

    def delete_model(self, model: str):
        """Delete a model from Ollama"""
        try:
            self.client.delete(model)
        except ollama.ResponseError as e:
            logger.error(f"Error deleting model: {e}")
            raise

    def generate_embeddings(
        self, input_text: Union[str, List[str]], truncate: bool = True
    ) -> Dict[str, Any]:
        """Generate embeddings for text input"""
        try:
            return self.client.embeddings(
                model=self.settings.model,
                prompt=input_text,
                options={"truncate": truncate},
            )
        except ollama.ResponseError as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def list_running_models(self) -> str:
        """List models currently loaded in memory"""
        try:
            response = self.client.ps()
            models = response.get("models", {})
            if not models:
                return "No models are currently loaded in memory."

            formatted_models = []
            for model in models:
                details = model.get("details", {})
                formatted_model = (
                    f"Name: {model.get('name')}\n"
                    f"Model: {model.get('model')}\n"
                    f"Size: {model.get('size')} bytes\n"
                    f"Digest: {model.get('digest')}\n"
                    f"Parent Model: {details.get('parent_model', 'N/A')}\n"
                    f"Format: {details.get('format')}\n"
                    f"Family: {details.get('family')}\n"
                    f"Families: {', '.join(details.get('families', []))}\n"
                    f"Parameter Size: {details.get('parameter_size')}\n"
                    f"Quantization Level: {details.get('quantization_level')}\n"
                    f"Expires At: {model.get('expires_at')}\n"
                    f"Size VRAM: {model.get('size_vram')} bytes\n"
                )
                formatted_models.append(formatted_model)

            return "\n\n".join(formatted_models)
        except Exception as e:
            logger.error(f"Error listing running models: {e}")
            return f"Error listing running models: {e}"

    def web_search(self, query: str) -> str:
        """Search the web for information"""
        logger.log("OLLAMA", f"Searching the web for: {query}")
        response = self.online_agent.search(query)
        if not response:
            return "No results found for user query."
        return response

    def load_model(self, model_name: str) -> None:
        """Load a model into memory"""
        self.client.generate(model=model_name)

    def unload_model(self, model_name: str) -> None:
        """Unload a model from memory"""
        self.client.generate(model=model_name, keep_alive=0)
