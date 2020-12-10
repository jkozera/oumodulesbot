import json
import logging
import os
import re
from typing import Iterable, List, Sequence

import discord
import pylru

from .backend import OUModulesBackend, Result
from .ou_utils import MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE

logger = logging.getLogger(__name__)

replies_cache = pylru.lrucache(1000)


class OUModulesBot(discord.Client):

    MENTION_RE = re.compile(r"!" + MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE)
    MODULES_COUNT_LIMIT = 5

    def __init__(self, *args, **kwargs):
        kwargs['intents'] = discord.Intents(messages=True)
        super().__init__(*args, **kwargs)
        self.backend = OUModulesBackend()

    async def process_mentions(self, message: discord.Message) -> None:
        """
        Process module code mentions from given `message`, and reply with
        thieir names/URLs if any were found.
        """
        results: List[Result] = []
        any_found = False
        for code in self.MENTION_RE.findall(message.content)[
            : self.MODULES_COUNT_LIMIT
        ]:
            code = code[1:].upper()
            result = await self.backend.find_result_for_code(code)
            if result:
                any_found = True
                results.append(result)
            else:
                results.append(Result(code, "not found", None))
        if any_found:
            # don't spam unless we're sure we at least found some results
            await self.post_results(message, results)

    def format_result(self, result: Result, for_embed: bool = False) -> str:
        """
        Return a string describing a module ready for posting to Discord,
        for given module `code` and `title`. Appends URL if available.

        Uses more compact formatting if `for_embed` is True, which should
        be used if multiple modules are presented as part of an embed.
        """
        fmt = " * {} " if for_embed else "{}"
        fmt_link = " * [{}]({}) " if for_embed else "{} (<{}>)"
        if result.url:
            text = fmt_link.format(result.title, result.url)
        else:
            text = fmt.format(result.title)

        # remove '!'s just in case, to avoid infinite circular bot invokation
        if for_embed:
            return text.replace("!", "")
        else:
            return "{}: {}".format(result.code, text).replace("!", "")

    def embed_results(
        self, embed: discord.Embed, results: Iterable[Result]
    ) -> None:
        """
        Adds `embed` fields for each provided module.
        """
        for result in results:
            embed.add_field(
                name=result.code,
                value=self.format_result(result, for_embed=True),
                inline=True,
            )

    async def post_results(
        self, message: discord.Message, results: Sequence[Result]
    ) -> None:
        """
        Create or update a bot message for given users's input message,
        and a list of modules.

        Message is updated instead of created if the input was already replied
        to, which means this time the input was edited.
        """
        modify_message = None
        if message.id in replies_cache:
            modify_message = replies_cache[message.id]

        embed = discord.Embed()
        if len(results) > 1:
            content = " "  # force removal when modifying
            self.embed_results(embed, results)
        elif len(results) == 1:
            content = self.format_result(results[0])
        else:
            logger.error("No results found!")
            # should never happen, but for safety let's make sure
            # that `content` is set below
            return

        if modify_message:
            await modify_message.edit(
                content=content, embed=embed if len(results) > 1 else None
            )
        else:
            replies_cache[message.id] = await message.channel.send(
                content, embed=embed if len(results) > 1 else None
            )

    async def on_message(self, message: discord.Message) -> None:
        await self.process_mentions(message)

    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        await self.process_mentions(after)


def main():
    logging.basicConfig(level="INFO")
    token = os.getenv("OU_BOT_TOKEN")
    if not token:
        with open("config.json", "r") as f:
            token = json.load(f)["token"]

    OUModulesBot().run(token)


if __name__ == "__main__":
    main()
