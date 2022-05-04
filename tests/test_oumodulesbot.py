import json
from collections import namedtuple
from unittest import mock

import discord
import pytest

from oumodulesbot.oumodulesbot import OUModulesBot

pytestmark = pytest.mark.asyncio


QUALIFICATION_URL_TPL = "http://www.open.ac.uk/courses/qualifications/{code}"


@pytest.fixture(autouse=True)
def mock_cache(monkeypatch):
    def mock_load(f):
        return {
            "A123": ["Mocked active module", "url1"],
            "A012": ["Mocked active short course", "url2"],
            "A888": ["Mocked active postgrad module", "url3"],
            "B321": ["Mocked inactive module", None],
            "B31": ["Mocked inactive-actually-active qualification", None],
        }

    monkeypatch.setattr(json, "load", mock_load)


ModuleExample = namedtuple("ModuleExample", "code,active,result")
E2E_EXAMPLES = [
    ModuleExample(
        "A123",
        True,
        ("A123: Mocked active module (<url1>)"),
    ),
    ModuleExample("B321", False, "B321: Mocked inactive module"),
    ModuleExample(
        "B31",
        False,
        "B31: Mocked inactive-actually-active qualification (<{url}>)".format(
            url=QUALIFICATION_URL_TPL.format(code="b31"),
        ),
    ),
    ModuleExample(
        "A012",
        True,
        ("A012: Mocked active short course (<url2>)"),
    ),
    ModuleExample(
        "A888",
        True,
        ("A888: Mocked active postgrad module (<url3>)"),
    ),
]


def create_mock_message(contents, send_result="foo", id_override=None):
    message = mock.Mock(spec=discord.Message)
    message.content = contents
    message.reply = mock.AsyncMock()
    message.reply.return_value = send_result
    message.id = id_override or contents
    return message


async def process_message(bot, message, result):
    """
    Pass the message to the bot, optionally verifying that appropriate checks
    are made for inactive modules.
    """

    with mock.patch("httpx.AsyncClient.head") as head_mock:
        if "actually-active" in result.result:
            head_mock.return_value.status_code = 200
            head_mock.return_value.url = result.code
        await bot.on_message(message)
        if not result.active:
            code = result.code.lower()
            # inactive results are double-checked with http to provide a link
            # in case the inactive cache.json status is no longer valid:
            if "qualification" not in result.result:
                prefix = "http://www.open.ac.uk/courses"
                urls = [
                    f"{prefix}/qualifications/details/{code}",
                    f"{prefix}/modules/{code}",
                ]
            else:
                urls = [QUALIFICATION_URL_TPL.format(code=code)]
            head_mock.assert_has_calls(
                [
                    mock.call(url, follow_redirects=True, timeout=3)
                    for url in urls
                ],
                any_order=True,
            )


@pytest.mark.parametrize("module", E2E_EXAMPLES)
async def test_end_to_end_create(module):
    """
    Basic test to make sure matching modules are processed correctly.

    Runs with each example from E2E_EXAMPLES independently.
    """
    bot = OUModulesBot()
    message = create_mock_message(f"foo !{module.code}")
    await process_message(bot, message, module)
    message.reply.assert_called_once_with(module.result, embed=None)


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
        f"foo !{first_post.code}",
        # result_message is our bot's response here:
        send_result=result_message,
        # the id must be the same to trigger `edit`:
        id_override="original_id",
    )
    await process_message(bot, message, first_post)

    for update in updates:
        update_message = create_mock_message(
            f"foo !{update.code}",
            id_override="original_id",
        )
        await process_message(bot, update_message, update)
        # verify that the bot's response is updated:
        result_message.edit.assert_called_once_with(
            content=update.result, embed=None
        )
        result_message.edit.reset_mock()


@mock.patch("httpx.AsyncClient.get")
async def test_end_to_end_missing_module(get_mock):
    bot = OUModulesBot()
    fake_module = ModuleExample("XYZ999", False, "XYZ999: Some Random Module")
    message = create_mock_message(f"foo !{fake_module.code}")

    # return matching data from httpx:
    # 1. Empty SPARQL:
    sparql_json = {"results": {"bindings": []}}
    get_mock.return_value.json = lambda: sparql_json

    # 2. OUDA HTML:
    get_mock.return_value.content = (
        "not really html but matches the regex:"
        f"<title>{fake_module.code} Some Random Module"
        " - Open University Digital Archive</title>"
    ).encode()

    # ensure module name is returned to Discord:
    await process_message(bot, message, fake_module)
    message.reply.assert_called_once_with(fake_module.result, embed=None)

    # ensure httpx was called with appropriate URL:
    get_mock.assert_called_with(
        # ignore SPARQL calls
        "http://www.open.ac.uk/library/digital-archive/module/"
        f"xcri:{fake_module.code}"
    )
