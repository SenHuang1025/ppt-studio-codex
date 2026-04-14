from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.services.theme_service import ThemeService


def test_theme_service_lists_all_presets_with_warm_orange_default(settings: Settings) -> None:
    service = ThemeService(settings=settings)

    themes = service.list_presets()

    assert [theme.id for theme in themes] == [
        "warm-orange",
        "business-blue",
        "fresh-green",
        "minimal-gray",
        "tech-dark",
    ]
    assert service.resolve_theme(None).id == "warm-orange"


def test_theme_service_renders_required_slide_variables(settings: Settings) -> None:
    service = ThemeService(settings=settings)

    warm_css = service.render_css_variables({"id": "warm-orange"})
    dark_css = service.render_css_variables({"id": "tech-dark"})

    required_variables = [
        "--slide-primary",
        "--slide-secondary",
        "--slide-accent",
        "--slide-bg",
        "--slide-surface",
        "--slide-surface-strong",
        "--slide-surface-soft",
        "--slide-text",
        "--slide-text-secondary",
        "--slide-border",
        "--slide-danger",
        "--slide-danger-soft",
        "--slide-neutral-soft",
        "--slide-font-title",
        "--slide-font-body",
        "--slide-radius-xl",
        "--slide-radius-lg",
        "--slide-radius-md",
        "--slide-shadow",
        "--slide-shadow-soft",
        "--slide-shadow-card",
        "--slide-primary-soft",
        "--slide-secondary-soft",
        "--slide-accent-soft",
        "--slide-grid-line",
    ]

    for variable_name in required_variables:
        assert variable_name in warm_css

    assert "color-scheme: light;" in warm_css
    assert "color-scheme: dark;" in dark_css


def test_theme_service_writes_preview_theme_file(settings: Settings, tmp_path: Path) -> None:
    preview_theme_file = tmp_path / "preview" / "variables.css"
    test_settings = settings.model_copy(update={"preview_theme_file_override": preview_theme_file})
    service = ThemeService(settings=test_settings)

    written_path = service.write_preview_theme({"id": "business-blue"})

    assert written_path == preview_theme_file.resolve()
    assert preview_theme_file.exists()
    payload = preview_theme_file.read_text(encoding="utf-8")
    assert "theme: business-blue" in payload
    assert "--slide-primary: #3b6ea8;" in payload
