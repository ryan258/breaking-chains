from forge.ui.view_models import markdown_heading_text


def test_markdown_heading_text_preserves_seed_text_without_interpreting_markup() -> None:
    seed = "Does **bold** cost $5?\n<script>alert(1)</script>"

    rendered = markdown_heading_text(seed)

    assert rendered == (r"Does \*\*bold\*\* cost \$5\? \<script\>alert\(1\)\<\/script\>")
    assert "\n" not in rendered
