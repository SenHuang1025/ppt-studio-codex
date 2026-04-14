from __future__ import annotations

from typing import Annotated, Any, Mapping, Literal

from pydantic import Field, field_validator

from app.schemas.base import APIModel

THEME_PRESET_IDS = (
    "warm-orange",
    "business-blue",
    "fresh-green",
    "minimal-gray",
    "tech-dark",
)
DEFAULT_THEME_ID = "warm-orange"

ThemeAppearance = Literal["light", "dark"]
ThemeAnimationStyle = Literal["calm", "dynamic", "minimal"]
ThemeValue = Annotated[str, Field(min_length=1)]


class ThemeColors(APIModel):
    primary: ThemeValue
    secondary: ThemeValue
    accent: ThemeValue
    background: ThemeValue
    surface: ThemeValue
    surfaceStrong: ThemeValue
    surfaceSoft: ThemeValue
    text: ThemeValue
    textSecondary: ThemeValue
    border: ThemeValue
    danger: ThemeValue
    dangerSoft: ThemeValue
    neutralSoft: ThemeValue
    primarySoft: ThemeValue
    secondarySoft: ThemeValue
    accentSoft: ThemeValue
    gridLine: ThemeValue


class ThemeFonts(APIModel):
    title: ThemeValue
    body: ThemeValue


class ThemeBorderRadius(APIModel):
    xl: ThemeValue
    lg: ThemeValue
    md: ThemeValue


class ThemeShadows(APIModel):
    default: ThemeValue
    soft: ThemeValue
    card: ThemeValue


class ThemeConfig(APIModel):
    id: str = Field(min_length=1)
    label: ThemeValue
    description: ThemeValue
    appearance: ThemeAppearance
    colors: ThemeColors
    fonts: ThemeFonts
    borderRadius: ThemeBorderRadius
    shadows: ThemeShadows
    animationStyle: ThemeAnimationStyle

    @field_validator("id")
    @classmethod
    def validate_theme_id(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in THEME_PRESET_IDS:
            raise ValueError(f"Unsupported theme id '{value}'.")
        return normalized


class ThemeListResponse(APIModel):
    themes: list[ThemeConfig] = Field(default_factory=list)


class ThemeSyncResponse(APIModel):
    theme: ThemeConfig


def resolve_theme_id(raw_theme: ThemeConfig | Mapping[str, Any] | None) -> str:
    if raw_theme is None:
        return DEFAULT_THEME_ID

    if isinstance(raw_theme, ThemeConfig):
        return raw_theme.id

    raw_id = raw_theme.get("id")
    if not isinstance(raw_id, str):
        return DEFAULT_THEME_ID

    normalized = raw_id.strip()
    return normalized or DEFAULT_THEME_ID
