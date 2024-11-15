import asyncio

import discord
from discord import app_commands

from ai.ollama_client import OllamaClient
from settings.manager import settings_manager
from utils.logger import logger


class DiscordService:
    def __init__(self, ollama: OllamaClient = None):
        self.initialized = False
        self.ollama = ollama
        self.settings = settings_manager.settings.discord
        self.allowed_users = []
        self.admin_users = []
        self.allowed_roles = []

        if self.validate():
            self.setup()
            self.initialized = True
        else:
            logger.error("Discord service not initialized")
            return

    def setup(self) -> bool:
        """Initialize the Discord client and commands"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)

        self._setup_events()
        self._setup_commands()
        return True

    def validate(self) -> bool:
        """Validate Discord settings"""
        if not self.settings.token:
            logger.error("DISCORD_TOKEN is not set")
            return False
        return True

    def _setup_events(self):
        """Setup Discord event handlers"""

        @self.client.event
        async def on_ready():
            await self.tree.sync()
            await self.client.change_presence(
                activity=discord.Activity(name="with God", type=0)
            )
            if self.client.guilds:
                logger.log(
                    "DISCORD",
                    f"Logged in as {self.client.user.name} on {self.client.guilds[0].name}",
                )
            else:
                logger.log("DISCORD", f"Logged in as {self.client.user.name}")
            logger.log("DISCORD", "Synced slash commands")
            logger.log("DISCORD", "Discord service is now ready!")

        @self.client.event
        async def on_error(event, *args, **kwargs):
            logger.exception(f"Discord error: {event}", exc_info=True)

        @self.client.event
        async def on_message(message):
            if message.author == self.client.user:
                return
            if self.client.user.mentioned_in(message):
                logger.log("DISCORD", f"{message.author}: {message.clean_content}")
                stripped_message = message.content.replace(
                    f"<@{self.client.user.id}>", ""
                ).strip()
                async with message.channel.typing():
                    response = self.ollama.chat(
                        messages=[{"role": "user", "content": stripped_message}]
                    )
                    await message.reply(response["content"])
                logger.log("DISCORD", f"Ollama replied to {message.author}")

    def _setup_commands(self):
        """Setup Discord slash commands"""

        @self.tree.command(name="chat", description="Chat with Ragnar!")
        async def chat_command(interaction: discord.Interaction, message: str):
            """Chat with Ragnar!"""
            logger.log("DISCORD", f"{interaction.user}: {message}")
            await interaction.response.defer()

            response = self.ollama.chat(messages=[{"role": "user", "content": message}])
            if not response:
                logger.error("No response from Ollama")
                await interaction.followup.send(
                    "Sorry, I encountered an error processing your message."
                )
                return

            if len(response["content"]) > 2000:
                logger.log("DISCORD", "Response is too long, sending as embed")
                embed = discord.Embed(
                    title="Ragnar's response",
                    description=response["content"],
                    color=0xF1C40F,
                )
                await interaction.followup.send(embed=embed)
            else:
                logger.log("DISCORD", "Response is short, sending as message")
                await interaction.followup.send(response["content"])

        @self.tree.command(name="ps", description="Get the running models from Ollama")
        async def ps_command(interaction: discord.Interaction):
            """Get the running models from Ollama"""
            available_models = self.ollama.list_models()
            await interaction.response.send_message(
                f"Available models: {', '.join(available_models)}"
            )

        @self.tree.command(
            name="set_temperature", description="Set the temperature for the AI model"
        )
        async def set_temperature_command(
            interaction: discord.Interaction, temperature: float
        ):
            """Set the temperature for the AI model"""
            previous_temperature = settings_manager.settings.ollama.temperature
            settings_manager.settings.ollama.temperature = temperature
            settings_manager.save()
            settings_manager.reload()
            await interaction.response.send_message(
                f"Temperature set to {temperature} (was {previous_temperature})"
            )

        @self.tree.command(name="set_model", description="Set the AI model to use")
        async def set_model_command(interaction: discord.Interaction, model: str):
            """Set the AI model to use"""
            await interaction.response.defer()

            try:
                available_models = self.ollama.list_models()
                if model not in available_models:
                    await interaction.response.send_message(
                        f"Model '{model}' not found. Available models: {', '.join(available_models)}"
                    )
                    return

                settings_manager.settings.ollama.model = model
                settings_manager.save()
                settings_manager.reload()
                async with interaction.channel.typing():
                    await interaction.followup.send(f"Model set to {model}")
            except Exception as e:
                logger.error(f"Error setting model: {e}")
                await interaction.followup.send(f"Unable to set model: {e}")

        @self.tree.command(
            name="web_search", description="Search the web for information"
        )
        async def web_search_command(interaction: discord.Interaction, query: str):
            """Search the web for information"""
            await interaction.response.defer()
            response = self.ollama.web_search(query)
            async with interaction.channel.typing():
                if len(response) > 2000:
                    logger.log("DISCORD", "Response is too long, sending as embed")
                    embed = discord.Embed(
                        title="Ragnar's response", description=response, color=0xF1C40F
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    logger.log("DISCORD", "Response is short, sending as message")
                    await interaction.followup.send(response)

    def run(self):
        """Thread entry point - starts the Discord bot"""
        try:
            self.client.run(self.settings.token, log_handler=None)
        except Exception as e:
            logger.error(f"Error in Discord service: {e}")

    async def _cleanup(self):
        """Async cleanup for Discord client"""
        if hasattr(self, "client"):
            await self.client.close()

    def stop(self):
        """Stop the Discord bot"""
        if not self.initialized or not self.running:
            return

        self.running = False

        # Get the client's event loop if it exists
        if hasattr(self, "client") and hasattr(self.client, "loop"):
            loop = self.client.loop
            if loop and loop.is_running():
                loop.create_task(self._cleanup())
            else:
                # If no running loop, create a new one
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self._cleanup())
                new_loop.close()

        logger.log("DISCORD", "Discord service stopped")
