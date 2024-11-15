import json
import os

from loguru import logger
from pydantic import ValidationError

from . import DATA_DIR
from .models import AppSettings, RagnarException


class SettingsManager:
    """Class that handles settings, ensuring they are validated against the AppSettings schema."""

    def __init__(self):
        self.filename = "settings.json"
        self.settings_file = DATA_DIR / self.filename

        os.makedirs(DATA_DIR, exist_ok=True)

        if not self.settings_file.exists():
            self.settings = AppSettings()
            self.save()
        else:
            self.load()

    def clean_settings(self, settings_dict: dict):
        """Remove keys from settings_dict that are not in the AppSettings model."""
        valid_keys = self.settings.model_dump().keys()
        cleaned_settings = {k: v for k, v in settings_dict.items() if k in valid_keys}
        self.settings = AppSettings.model_validate(cleaned_settings)

    def load(self, settings_dict: dict | None = None):
        """Load settings from file, validating against the AppSettings schema."""
        try:
            if not settings_dict:
                with open(self.settings_file, "r", encoding="utf-8") as file:
                    settings_dict = json.loads(file.read())
            self.settings = AppSettings.model_validate(settings_dict)
            self.clean_settings(settings_dict)
            self.save()
        except ValidationError as e:
            logger.error(f"Error validating settings: {e}")
            raise RagnarException(f"Validation error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing settings file: {e}")
            raise RagnarException(f"JSON decode error: {e}")
        except FileNotFoundError as e:
            logger.warning(
                f"Error loading settings: {self.settings_file} does not exist"
            )
            raise RagnarException(f"File not found: {e}")

    def save(self):
        """Save settings to file, using Pydantic model for JSON serialization."""
        with open(self.settings_file, "w", encoding="utf-8") as file:
            file.write(self.settings.model_dump_json(indent=4))


settings_manager = SettingsManager()
