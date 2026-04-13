import { defineConfig, presetAttributify, presetTypography, presetUno } from 'unocss'
import transformerDirectives from '@unocss/transformer-directives'
import transformerVariantGroup from '@unocss/transformer-variant-group'

export default defineConfig({
  presets: [presetUno(), presetAttributify(), presetTypography()],
  transformers: [transformerDirectives(), transformerVariantGroup()],
  shortcuts: {
    'app-shell': 'min-h-screen text-[color:var(--app-text-primary)] antialiased',
    'glass-panel':
      'rounded-[var(--radius-xl)] border border-[color:var(--app-glass-border)] bg-[color:var(--app-glass-bg)] shadow-[var(--shadow-glass-1)] backdrop-blur-xl',
    'glass-panel-soft': 'glass-panel bg-[color:var(--app-glass-bg-soft)]',
    'glass-panel-strong': 'glass-panel bg-[color:var(--app-glass-bg-strong)] shadow-[var(--shadow-glass-2)]',
    'content-panel': 'rounded-[var(--radius-2xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor)] shadow-[var(--shadow-canvas)]',
    'content-panel-subtle': 'rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-editor-2)]',
    'highlight-ring-primary': 'ring-1 ring-inset ring-[color:var(--app-primary-ring)] shadow-[var(--shadow-highlight)]',
    'highlight-ring-accent': 'ring-1 ring-inset ring-[color:var(--app-accent-ring)] shadow-[var(--shadow-accent)]',
    'gradient-text-primary': 'bg-[var(--gradient-brand)] bg-clip-text text-transparent',
    'interactive-lift': 'transition duration-250 ease-out hover:-translate-y-0.5 hover:border-[color:var(--app-border-strong)] hover:shadow-[var(--shadow-hover)]',
    'workspace-surface': 'bg-[linear-gradient(180deg,var(--surface-editor)_0%,var(--surface-editor-2)_100%)]',
    'mono-meta': 'font-[var(--font-family-mono)] tracking-[0.18em] uppercase'
  }
})
