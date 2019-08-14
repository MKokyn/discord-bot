import os
import re
import logging
import traceback
import importlib

from shlex import split
from types import ModuleType
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Set, Pattern

import discord

from constants import BASE_DIR
from command import BaseCommand, CommandResult
from context import Context
from argparser.arguments import Arguments
from argparser.exceptions import ParserError


if TYPE_CHECKING:
    from bot import TarakaniaRPG

COMMANDS_DIR = os.sep.join((BASE_DIR, "commands"))


log = logging.getLogger(__name__)


class CommandCheckError(Exception):
    pass


class Handler:
    def __init__(self, bot: "TarakaniaRPG"):
        self.bot = bot

        self._custom_prefixes: Dict[int, str] = {}
        self._commands: Dict[str, BaseCommand] = {}
        self._imported: Dict[str, ModuleType] = {}

    async def load_command(
        self, command_path: str, raise_on_error: bool = False
    ) -> Optional[BaseCommand]:
        name = command_path.rsplit(os.sep, 1)[1][8:-3]
        module_path = command_path.replace(os.sep, ".")[:-3]

        try:
            log.info(f"Loading {name}")
            imported = importlib.import_module(module_path)
            log.debug(f"Creating instance of {name}")
            command = getattr(imported, "Command")(self.bot)
        except Exception:
            log.exception(f"Error loading {name}")

            if raise_on_error:
                raise

            return None

        for alias in command.aliases:
            self._commands[alias] = command

        self._imported[command.name] = imported

        return command

    async def reload_command(
        self, name: str, raise_on_error: bool = False
    ) -> Optional[BaseCommand]:
        imported = self._imported.get(name)
        if imported is None:
            return None

        old_aliases = self._commands[name].aliases

        try:
            log.info(f"Reloading {name}")
            reloaded = importlib.reload(imported)
            log.debug(f"Creating instance of {name}")
            command = getattr(reloaded, "Command")(self.bot)
        except Exception:
            log.exception(f"Error reloading {name}")

            if raise_on_error:
                raise

            return None
        finally:
            for alias in old_aliases:
                del self._commands[alias]

        for alias in command.aliases:
            self._commands[alias] = command

        self._imported[name] = reloaded

        return command

    async def load_all_commands(self) -> None:
        commands_found = []

        for path, dirs, files in os.walk(COMMANDS_DIR):
            for f in files:
                if f.startswith("command_") and f.endswith(".py"):
                    full_path = os.sep.join((path, f))
                    relative_path = os.path.relpath(full_path)
                    commands_found.append(
                        os.sep.join(relative_path.split(os.sep)[1:])
                    )

        log.info("Started loading commands")
        for command_path in commands_found:
            await self.load_command(command_path)
        log.info(f"Loaded commands with {len(self._commands)} aliases")

    async def prepare_prefixes(self) -> None:
        bot_id = self.bot.user.id

        prefixes = (
            re.escape(self.bot.config["default-prefix"]),
            f"<@{bot_id}>",
            f"<@!{bot_id}>",
        )

        self._prefixes_regex = re.compile(
            fr"^({'|'.join(prefixes)})\s*", re.IGNORECASE
        )
        self._dm_prefixes_regex = re.compile(
            fr"^({'|'.join(prefixes+('',))})\s*", re.IGNORECASE
        )

        await self.prepare_custom_prefixes()

        log.debug("Prepareded prefixes")

    async def prepare_custom_prefixes(self) -> None:
        # TODO

        pass

    def separate_prefix(
        self, content: str, guild_id: Optional[int]
    ) -> Tuple[Optional[str], str]:
        def regex_match(
            expr: Pattern[str], content: str
        ) -> Tuple[Optional[str], str]:
            match = expr.search(content)
            if match is None:
                return None, content

            return match[1], content[match.end(0) :]

        if guild_id is None:
            return regex_match(self._dm_prefixes_regex, content)

        custom_prefix = self._custom_prefixes.get(guild_id)
        if custom_prefix is None:
            return regex_match(self._prefixes_regex, content)

        lower_content = content.lower()
        if lower_content.startswith(custom_prefix):
            return (custom_prefix, content[len(custom_prefix) :].rstrip())

        return None, content

    async def process_message(self, msg: discord.Message) -> None:
        await self.bot.wait_until_ready()

        if msg.author.bot:
            return

        used_prefix, trimmed_content = self.separate_prefix(
            msg.content, msg.guild.id if msg.guild else None
        )

        if used_prefix is None:
            return

        try:
            splitted_content = split(trimmed_content)
        except ValueError:
            # TODO: better help message
            await msg.channel.send(
                "Ошибка разделения аргументов: открытая ковычка"
            )

            return

        args = Arguments(splitted_content)

        used_alias = args.command
        if used_alias is None:
            return

        command = self._commands.get(used_alias)
        if command is None:
            return

        ctx = Context(self.bot, msg, command, used_prefix, used_alias)

        try:
            await self.run_command_checks(ctx)
            await args.convert(ctx, command.arguments)
        except (CommandCheckError, ParserError) as e:
            return await self.process_response(
                f"Ошибка при обработке команды **{command.name}**: {e}\n"
                f"Правила вызова команды: `{await command.get_usage(ctx)}`",
                ctx,
            )

        log.debug(
            f"Invoking command {command.name} from {ctx.author.id} in channel {ctx.channel.id}"
        )

        try:
            await self.process_response(await command.run(ctx, args), ctx)
        except Exception:
            log.exception(f"Error calling command {command.name}")

            await self.process_response(
                (
                    f"Ошибка при выполнении команды **{command.name}**:\n"
                    f"```{traceback.format_exc(3)}```"
                ),
                ctx,
            )

    async def run_command_checks(self, ctx: Context) -> None:
        if ctx.command.guild_only and ctx.guild is None:
            raise CommandCheckError(
                "Данную команду можно использовать только на сервере"
            )

        if (
            ctx.command.owner_only
            and ctx.author.id not in self.bot.config["owners"]
        ):
            raise CommandCheckError(
                "Данную команду могут использовать только владельцы бота"
            )

    async def process_response(
        self, response: CommandResult, ctx: Context
    ) -> None:
        if isinstance(response, str):
            await ctx.send(response)
        elif isinstance(response, discord.Message):
            return
        elif response is None:
            return
        else:
            raise TypeError(
                f"Invalid type returned by command {ctx.command.name}: {type(response)}"
            )

    def get_command(self, name: str) -> Optional[BaseCommand]:
        return self._commands.get(name)

    def get_all_commands(self, with_hidden: bool = False) -> Set[BaseCommand]:
        return set(
            c for c in self._commands.values() if not c.hidden or with_hidden
        )
