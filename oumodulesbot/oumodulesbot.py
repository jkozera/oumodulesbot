import contextlib
import datetime
import json
import logging
import os
import re
from typing import Iterable, List, Sequence

import discord
import pylru
from google.cloud import firestore  # type: ignore

from .backend import OUModulesBackend, Result
from .ou_utils import MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE

logger = logging.getLogger(__name__)

replies_cache = pylru.lrucache(1000)


if os.environ.get("DISABLE_FIRESTORE") != "1":
    firestore_db = firestore.AsyncClient(project="ou-modules-bot")


@firestore.async_transactional
async def _db_claim_message(transaction, message_id, value) -> bool:
    doc_ref = firestore_db.collection("message_ids").document(str(message_id))
    snapshot = await doc_ref.get(transaction=transaction)
    claimed = snapshot.exists and not snapshot.get("can_retry")
    if not claimed:
        data = {"claimed": value, "can_retry": False}
        if snapshot.exists:
            transaction.update(doc_ref, data)
        else:
            transaction.create(doc_ref, data)
    return not claimed


async def _db_retry_message(message_id) -> None:
    doc_ref = firestore_db.collection("message_ids").document(str(message_id))
    await doc_ref.update(doc_ref, {"can_retry": True})


@contextlib.asynccontextmanager
async def claim_message(message_id):
    if os.environ.get("DISABLE_FIRESTORE") == "1":
        yield True
        return
    if await _db_claim_message(
        firestore_db.transaction(), message_id, datetime.datetime.now()
    ):
        try:
            yield True
        except Exception:
            # Nothing has been posted yet.
            await _db_retry_message(firestore_db.transaction(), message_id)
    else:
        yield False


class OUModulesBot(discord.Client):
    MENTION_RE = re.compile(r"!" + MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE)
    MODULES_COUNT_LIMIT = 5

    def __init__(self, *args, **kwargs):
        kwargs["intents"] = discord.Intents(
            messages=True,
            message_content=True,
            guilds=True,
        )
        super().__init__(*args, **kwargs)
        self.backend = OUModulesBackend()

    async def process_mentions(self, message: discord.Message) -> None:
        """
        Process module code mentions from given `message`, and reply with
        their names/URLs if any were found.
        """
        results: List[Result] = []
        matches = list(
            self.MENTION_RE.findall(message.content)[
                : self.MODULES_COUNT_LIMIT
            ]
        )
        any_found = False
        if matches:
            async with claim_message(message.id) as claimed:
                if not claimed:
                    return
                for code in matches:
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

        embeds = [embed] if len(results) > 1 else []
        if modify_message:
            await modify_message.edit(content=content, embeds=embeds)
        else:
            replies_cache[message.id] = await message.reply(
                content, embeds=embeds
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
