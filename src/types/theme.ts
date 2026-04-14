export const THEME_PRESET_IDS = [
  'warm-orange',
  'business-blue',
  'fresh-green',
  'minimal-gray',
  'tech-dark'
] as const

export type ThemePresetId = (typeof THEME_PRESET_IDS)[number]

export const THEME_APPEARANCE_VALUES = ['light', 'dark'] as const

export type ThemeAppearance = (typeof THEME_APPEARANCE_VALUES)[number]

export const THEME_ANIMATION_STYLE_VALUES = ['calm', 'dynamic', 'minimal'] as const

export type ThemeAnimationStyle = (typeof THEME_ANIMATION_STYLE_VALUES)[number]

export const DEFAULT_PREVIEW_THEME_ID: ThemePresetId = 'warm-orange'

export interface ThemeColors {
  accent: string
  accentSoft: string
  background: string
  border: string
  danger: string
  dangerSoft: string
  gridLine: string
  neutralSoft: string
  primary: string
  primarySoft: string
  secondary: string
  secondarySoft: string
  surface: string
  surfaceSoft: string
  surfaceStrong: string
  text: string
  textSecondary: string
}

export interface ThemeFonts {
  body: string
  title: string
}

export interface ThemeBorderRadius {
  lg: string
  md: string
  xl: string
}

export interface ThemeShadows {
  card: string
  default: string
  soft: string
}

export interface ThemeConfig {
  animationStyle: ThemeAnimationStyle
  appearance: ThemeAppearance
  borderRadius: ThemeBorderRadius
  colors: ThemeColors
  description: string
  fonts: ThemeFonts
  id: ThemePresetId
  label: string
  shadows: ThemeShadows
}

export interface ThemeListResponse {
  themes: ThemeConfig[]
}

export interface ThemeSyncResponse {
  theme: ThemeConfig
}
