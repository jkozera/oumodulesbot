import pytest

from oumodulesbot import backend


@pytest.mark.parametrize(
    "html, expected_name",
    [
        (
            "<title>\n	 MST125 | Essential Mathematics 2\n</title>",
            "Essential Mathematics 2",
        ),
        (
            (
                "<title>\nD241 - Exploring mental health and counselling"
                " | Open University</title>"
            ),
            "Exploring mental health and counselling",
        ),
        (
            (
                "<title>\n\tMechanical Engineering | Open University | T329"
                "\n</title>"
            ),
            "Mechanical Engineering",
        ),
    ],
)
def test_html_title_in_html(html, expected_name):
    assert backend.find_title_in_html(html) == expected_name
