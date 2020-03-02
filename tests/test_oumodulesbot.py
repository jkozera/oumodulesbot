from collections import namedtuple
import json
from unittest import mock

import discord
import pytest

from oumodulesbot.oumodulesbot import OUModulesBot

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def mock_cache(monkeypatch):
    def mock_load(f):
        return [
            {"A123": ["Mocked active module", True]},
            {"A012": ["Mocked active short course", True]},
            {"A888": ["Mocked active postgrad module", True]},
            {"B321": ["Mocked inactive module", False]},
        ]

    monkeypatch.setattr(json, "load", mock_load)


examples_fields = "module_code,active,expected_result"
ModuleExample = namedtuple("ModuleExample", examples_fields)
E2E_EXAMPLES = [
    ModuleExample(
        "A123",
        True,
        (
            "A123: Mocked active module"
            " (http://www.open.ac.uk/courses/modules/a123)"
        ),
    ),
    ModuleExample("B321", False, "B321: Mocked inactive module"),
    ModuleExample(
        "A012",
        True,
        (
            "A012: Mocked active short course"
            " (http://www.open.ac.uk/courses/short-courses/a012)"
        ),
    ),
    ModuleExample(
        "A888",
        True,
        (
            "A888: Mocked active postgrad module"
            " (http://www.open.ac.uk/postgraduate/modules/a888)"
        ),
    ),
]


def create_mock_message(contents, send_result="foo", id_override=None):
    message = mock.Mock(spec=discord.Message)
    message.content = contents
    message.channel.send = mock.AsyncMock()
    message.channel.send.return_value = send_result
    message.id = id_override or contents
    return message


async def process_message(bot, message, has_inactive_module):
    """
    Pass the message to the bot, optionally verifying that appropriate checks
    are made for inactive modules.
    """

    with mock.patch("httpx.AsyncClient.head") as head_mock:
        await bot.on_message(message)
        if has_inactive_module:
            # inactive modules are double-checked with http to provide a link
            # in case the inactive cache.json status is no longer valid:
            head_mock.assert_called_once_with(
                "http://www.open.ac.uk/courses/modules/b321"
            )


@pytest.mark.parametrize(examples_fields, E2E_EXAMPLES)
async def test_end_to_end_create(module_code, active, expected_result):
    """
    Basic test to make sure matching modules are processed correctly.

    Runs with each example from E2E_EXAMPLES independently.
    """
    bot = OUModulesBot()
    message = create_mock_message(f"foo !{module_code}")
    await process_message(bot, message, has_inactive_module=not active)
    message.channel.send.assert_called_once_with(expected_result, embed=None)


async def test_end_to_end_update():
    """
    Ensure `message.edit` on the original reply is called, instead of
    `channel.send`, if the triggering message is edited, as opposed to new.

    Processes E2E_EXAMPLES sequentially with a single bot instance.
    First message is the first example, which is subsequently edited
    by replacing its contents with further examples.
    """
    first_post, updates = E2E_EXAMPLES[0], E2E_EXAMPLES[1:]
    bot = OUModulesBot()
    result_message = mock.Mock(spec=discord.Message)
    message = create_mock_message(
        f"foo !{first_post.module_code}",
        # result_message is our bot's response here:
        send_result=result_message,
        # the id must be the same to trigger `edit`:
        id_override="original_id",
    )
    await process_message(bot, message, not first_post.active)

    for update in updates:
        update_message = create_mock_message(
            f"foo !{update.module_code}", id_override="original_id",
        )
        await process_message(bot, update_message, not update.active)
        # verify that the bot's response is updated:
        result_message.edit.assert_called_once_with(
            content=update.expected_result, embed=None
        )
        result_message.edit.reset_mock()
