import dataclasses
import logging
from typing import Callable, List

LOGGER = logging.getLogger("line-webhook-cmd")


class NoCommandError(Exception):
    pass


class UnknownCommandError(Exception):
    cmd_name: str

    def __init__(self, cmd_name):
        self.cmd_name = cmd_name


class MissingArgumentsError(Exception):
    cmd_name: str
    missing_args: list[str]

    def __init__(self, cmd_name, missing_args):
        self.cmd_name = cmd_name
        self.missing_args = missing_args


@dataclasses.dataclass
class Command:
    name: str
    func: Callable
    required_args: List[str]


class CommandBuilder:
    def __init__(self):
        self.commands = {}

    def register_command(self, name: str, func: Callable, required_args: List[str] = ()):
        LOGGER.debug(f"Registering command {name} with args {required_args}")
        self.commands[name] = Command(name, func, required_args)

    def parse_and_execute(self, command_string, ctx=None):
        LOGGER.debug(f"Parsing command {command_string}")

        parts = command_string.split()
        if not parts:
            raise NoCommandError("No command provided")

        command_name, *args = parts

        command_name = command_name.lower()
        if command_name not in self.commands:
            raise UnknownCommandError(command_name)

        command = self.commands[command_name]

        if len(args) < len(command.required_args):
            raise MissingArgumentsError(command_name, command.required_args)

        return command.func(*args, ctx=ctx)
