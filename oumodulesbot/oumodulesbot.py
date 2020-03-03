import json
import logging
import os
import re

import discord
import pylru

from .backend import OUModulesBackend
from .ou_utils import MODULE_CODE_RE_TEMPLATE

logger = logging.getLogger(__name__)

replies_cache = pylru.lrucache(1000)


class OUModulesBot(discord.Client):

    MENTION_RE = re.compile(r"!" + MODULE_CODE_RE_TEMPLATE)
    MODULES_COUNT_LIMIT = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = OUModulesBackend()

    async def do_mentions(self, message):
        modules = []
        any_found = False
        for module in self.MENTION_RE.findall(message.content)[
            : self.MODULES_COUNT_LIMIT
        ]:
            module_code = module[1:].upper()
            title = await self.backend.get_module_title(module_code)
            if title:
                any_found = True
                modules.append((module_code, title))
            else:
                modules.append((module_code, "not found"))
        if any_found:
            # don't spam unless we're sure we at least found some modules
            await self.post_modules(message, modules)

    async def format_course(self, code, title, for_embed=False):
        fmt = " * {} " if for_embed else "{}"
        fmt_link = " * [{}]({}) " if for_embed else "{} ({})"
        url = await self.backend.get_module_url(code)
        if url:
            result = fmt_link.format(title, url)
        else:
            result = fmt.format(title)
        if for_embed:
            return result
        else:
            return "{}: {}".format(code, result)

    async def _embed_modules(self, embed, modules):
        for (code, title) in modules:
            embed.add_field(
                name=code,
                value=await self.format_course(code, title, for_embed=True),
                inline=True,
            )

    async def post_modules(self, message, modules):
        modify_message = None
        if message.id in replies_cache:
            modify_message = replies_cache[message.id]

        embed = discord.Embed()
        if len(modules) > 1:
            content = " "  # force removal when modifying
            await self._embed_modules(embed, modules)
        elif len(modules) > 0:
            code, title = modules[0]
            content = await self.format_course(code, title)
        else:
            logger.error("No modules found!")
            # should never happen, but for safety let's make sure
            # that `content` is set below
            return

        if modify_message:
            await modify_message.edit(
                content=content, embed=embed if len(modules) > 1 else None
            )
        else:
            replies_cache[message.id] = await message.channel.send(
                content, embed=embed if len(modules) > 1 else None
            )

    async def on_message(self, message):
        await self.do_mentions(message)

    async def on_message_edit(self, before, after):
        await self.do_mentions(after)


def main():
    logging.basicConfig(level="INFO")
    token = os.getenv("OU_BOT_TOKEN")
    if not token:
        with open("config.json", "r") as f:
            token = json.load(f)["token"]

    OUModulesBot().run(token)


if __name__ == "__main__":
    main()
