import os
import threading
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from ai.ollama_client import OllamaClient
from services.discord import DiscordService
from settings import DATA_DIR, get_version
from settings.manager import settings_manager
from utils.logger import log_cleaner, logger


class Program(threading.Thread):
    """Main program thread"""

    def __init__(self):
        """Initialize the program"""
        super().__init__(name="Ragnar")
        self.initialized = False
        self.running = False
        self.settings = settings_manager.settings
        self.ollama: OllamaClient = OllamaClient()
        if not self.ollama.initialized:
            logger.error("Failed to initialize Ollama client")
            return

        self.services = {}

        try:
            self.discord: DiscordService = DiscordService(self.ollama)
            self.discord.client.run(self.settings.discord.token, log_handler=None)
        except Exception:
            return

    def validate_services(self):
        """Validate services"""
        return any(
            service_instance.validate() for service_instance in self.services.values()
        )

    def start(self):
        """Start the program"""
        latest_version = get_version()
        logger.log("PROGRAM", f"Ragnar v{latest_version} started!")

        os.makedirs(DATA_DIR, exist_ok=True)
        if not settings_manager.settings_file.exists():
            logger.log("PROGRAM", "Settings file not found, creating default settings")
            settings_manager.save()

        if not self.validate_services():
            logger.log("PROGRAM", "----------------------------------------------")
            logger.error("Ragnar is waiting for configuration to start!")
            logger.log("PROGRAM", "----------------------------------------------")

        while not self.validate_services():
            time.sleep(1)

        if self.services:
            for service in self.services.values():
                service.start()

        self.executors = []
        self.scheduler = BackgroundScheduler()
        self._schedule_functions()

        super().start()
        self.scheduler.start()
        self.initialized = True
        logger.success("Ragnar is running!")

    def _schedule_functions(self) -> None:
        """Schedule each function based on its interval."""
        scheduled_functions = {log_cleaner: {"interval": 60 * 60}}

        for func, config in scheduled_functions.items():
            self.scheduler.add_job(
                func,
                "interval",
                seconds=config["interval"],
                args=config.get("args"),
                id=f"{func.__name__}",
                max_instances=config.get("max_instances", 1),
                replace_existing=True,
                next_run_time=datetime.now(),
                misfire_grace_time=30,
            )
            logger.debug(
                f"Scheduled {func.__name__} to run every {config['interval']} seconds."
            )

    def run(self):
        """Run the program"""
        self.running = True

        logger.log("PROGRAM", "Listening for events...")

        while self.running:
            time.sleep(1)

    def stop(self):
        """Stop all services and cleanup"""
        self.running = False

        if not self.initialized:
            return

        if self.ollama.running_models:
            for model in self.ollama.running_models:
                logger.log("OLLAMA", f"Unloading model: {model.name}")
                self.ollama.unload_model(model.name)

        for service in self.services.values():
            if service.initialized:
                service.stop()

        if hasattr(self, "scheduler") and self.scheduler.running:
            self.scheduler.shutdown(wait=False)

        logger.log("PROGRAM", "Ragnar has been stopped.")
