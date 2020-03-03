import json
import logging
import os
import re

import discord
import httpx
import pylru

from .ou_utils import get_module_url

logger = logging.getLogger(__name__)

replies_cache = pylru.lrucache(1000)


class OUModulesBot(discord.Client):

    MODULE_RE = re.compile(
        r"<title>[a-zA-Z]{1,3}[0-9]{1,3} (.*)"
        " - Open University Digital Archive</title>"
    )

    EMBED_RE = re.compile(r"![a-zA-Z]{1,3}[0-9]{1,3}")
    MODULES_COUNT_LIMIT = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open("cache.json", "r") as f:
            self.cache = json.load(f)

    async def get_module_title(self, code):
        if code.upper() in self.cache:
            return self.cache[code.upper()][0].replace("!", "")
        else:
            logger.info("{} not in cache".format(code))
        try:
            url_template = (
                "http://www.open.ac.uk/library/digital-archive/module/xcri:{}"
            )
            async with httpx.AsyncClient() as client:
                response = await client.get(url_template.format(code))
            html = response.content.decode("utf-8")
        except Exception:
            return
        title = self.MODULE_RE.findall(html)
        return title[0].replace("!", "") if title else None

    async def do_embeds(self, message):
        modules = []
        any_found = False
        for module in self.EMBED_RE.findall(message.content)[
            : self.MODULES_COUNT_LIMIT
        ]:
            title = await self.get_module_title(module[1:].upper())
            if title:
                any_found = True
                modules.append((module[1:].upper(), title))
            else:
                modules.append((module[1:].upper(), "not found"))
        if any_found:
            # don't spam unless we're sure we at least found some modules
            # (different from 'command' mode, where we may reply even if
            #  we can't find any)
            await self.post_modules(message, modules)

    async def _check_is_module(self, url, code):
        async with httpx.AsyncClient() as client:
            response = await client.head(url, allow_redirects=True)
            correct_redirect = code.lower() in str(response.url).lower()
            return correct_redirect and response.status_code == 200

    async def format_course(self, code, title, for_embed=False):
        fmt = " * {} " if for_embed else "{}"
        fmt_link = " * [{}]({}) " if for_embed else "{} ({})"
        cached_url = self.cache.get(code, ["", ""])[1]
        try_url = cached_url or get_module_url(code)
        if cached_url or await self._check_is_module(try_url, code):
            result = fmt_link.format(title, try_url)
        else:
            result = fmt.format(title)
        if for_embed:
            return result
        else:
            return "{}: {}".format(code, result)

    async def post_modules(self, message, modules):
        modify_message = None
        if message.id in replies_cache:
            modify_message = replies_cache[message.id]

        embed = discord.Embed()
        if len(modules) > 1:
            content = " "  # force removal when modifying
            for (code, title) in modules:
                embed.add_field(
                    name=code,
                    value=await self.format_course(
                        code, title, for_embed=True
                    ),
                    inline=True,
                )
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
        await self.do_embeds(message)

    async def on_message_edit(self, before, after):
        await self.do_embeds(after)


def main():
    logging.basicConfig(level="INFO")
    token = os.getenv("OU_BOT_TOKEN")
    if not token:
        with open("config.json", "r") as f:
            token = json.load(f)["token"]

    OUModulesBot().run(token)


if __name__ == "__main__":
    main()
