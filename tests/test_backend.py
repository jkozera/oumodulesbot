import pytest

from oumodulesbot import backend


@pytest.mark.parametrize(
    "html, expected_name",
    [
        (
            "<title>\n	 MST125 | Essential Mathematics 2 "
            "| Open University\n</title>",
            "Essential Mathematics 2",
        ),
        (
            "<title>\nD241 - Exploring mental health and counselling "
            "- Open University Course\n</title>",
            "Exploring mental health and counselling",
        ),
    ],
)
def test_html_title_in_html(html, expected_name):
    assert backend.find_title_in_html(html) == expected_name
