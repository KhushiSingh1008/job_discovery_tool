from app.scraper.normalize.text import clean_text, html_to_text


def test_clean_text_collapses_whitespace_and_unescapes() -> None:
    assert clean_text("  Barista\n\t&amp; Team   Member ") == "Barista & Team Member"
    assert clean_text(None) == ""


def test_html_to_text_handles_escaped_markup() -> None:
    text = html_to_text(
        "&lt;p&gt;Hello&lt;/p&gt;&lt;ul&gt;&lt;li&gt;One&lt;/li&gt;&lt;li&gt;Two&lt;/li&gt;&lt;/ul&gt;"
    )
    assert text.splitlines() == ["Hello", "One", "Two"]


def test_html_to_text_limits_blank_lines() -> None:
    assert html_to_text("<p>A</p>\n\n\n  \n\n<p>B</p>") == "A\n\nB"
