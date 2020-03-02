import asyncio
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


E2E_EXAMPLES = [
    (
        "A123",
        True,
        (
            "A123: Mocked active module"
            " (http://www.open.ac.uk/courses/modules/a123)"
        ),
    ),
    ("B321", False, "B321: Mocked inactive module"),
    (
        "A012",
        True,
        (
            "A012: Mocked active short course"
            " (http://www.open.ac.uk/courses/short-courses/a012)"
        ),
    ),
    (
        "A888",
        True,
        (
            "A888: Mocked active postgrad module"
            " (http://www.open.ac.uk/postgraduate/modules/a888)"
        ),
    ),
]


def create_mock_message(contents, send_result="foo"):
    message = mock.Mock(spec=discord.Message)
    message.content = contents
    send_result = asyncio.Future()
    send_result.set_result(send_result)
    message.channel.send.return_value = send_result
    message.id = contents
    return message


@pytest.mark.parametrize("module_code,active,expected_result", E2E_EXAMPLES)
async def test_end_to_end_create(module_code, active, expected_result):
    bot = OUModulesBot()
    message = create_mock_message(f"foo !{module_code}")
    with mock.patch("httpx.AsyncClient.head") as head_mock:
        await bot.on_message(message)
        if not active:
            # inactive modules are double-checked with http to provide a link
            # in case the inactive cache.json status is no longer valid:
            head_mock.assert_called_once_with(
                "http://www.open.ac.uk/courses/modules/b321"
            )
    message.channel.send.assert_called_once_with(expected_result, embed=None)
