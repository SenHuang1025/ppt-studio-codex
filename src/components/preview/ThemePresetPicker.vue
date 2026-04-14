<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NSkeleton, NTag } from 'naive-ui'
import type { ThemeAnimationStyle, ThemeConfig } from '@/types/theme'

const props = withDefaults(defineProps<{
  activeThemeId: string
  applyingThemeId?: string | null
  error?: string | null
  loading?: boolean
  syncing?: boolean
  themes: ThemeConfig[]
}>(), {
  applyingThemeId: null,
  error: null,
  loading: false,
  syncing: false
})

const emit = defineEmits<{
  apply: [theme: ThemeConfig]
  retry: []
}>()

const skeletonItems = computed<number[]>(() => Array.from({ length: 5 }, (_, index) => index))

function resolveAppearanceLabel(theme: ThemeConfig): string {
  return theme.appearance === 'dark' ? '暗色' : '浅色'
}

function resolveAnimationLabel(style: ThemeAnimationStyle): string {
  switch (style) {
    case 'dynamic':
      return '灵动'
    case 'minimal':
      return '克制'
    default:
      return '平缓'
  }
}

function isActiveTheme(theme: ThemeConfig): boolean {
  return props.activeThemeId === theme.id
}

function isApplyingTheme(theme: ThemeConfig): boolean {
  return props.applyingThemeId === theme.id
}

function applyTheme(theme: ThemeConfig): void {
  if (props.loading || props.syncing || props.applyingThemeId || isActiveTheme(theme)) {
    return
  }

  emit('apply', theme)
}
</script>

<template>
  <section class="grid gap-3">
    <div class="flex items-start justify-between gap-3">
      <div>
        <div class="mono-meta mb-2 text-[color:var(--app-text-tertiary)]">PPT 页面主题</div>
        <h3 class="m-0 text-base font-semibold">预览主题</h3>
        <p class="mt-2 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          选择后会写回项目主题配置，并同步重写 preview server 的 `variables.css`。
        </p>
      </div>
      <NButton quaternary size="small" @click="emit('retry')">重试</NButton>
    </div>

    <div
      v-if="error"
      class="rounded-[var(--radius-xl)] border border-[rgba(183,91,53,0.18)] bg-[rgba(255,248,237,0.82)] px-4 py-3 text-sm leading-6 text-[color:#9f4b2a]"
    >
      {{ error }}
    </div>

    <div
      v-else-if="syncing"
      class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[color:var(--surface-card)] px-4 py-3 text-sm text-[color:var(--app-text-secondary)]"
    >
      正在同步当前项目主题到 preview server...
    </div>

    <div v-if="loading && themes.length === 0" class="grid gap-3">
      <div
        v-for="item in skeletonItems"
        :key="item"
        class="rounded-[var(--radius-xl)] border border-[color:var(--app-border-subtle)] bg-[rgba(255,255,255,0.68)] p-4"
      >
        <NSkeleton :sharp="false" height="18px" width="46%" />
        <NSkeleton class="mt-3" :sharp="false" height="14px" width="100%" />
        <div class="mt-4 grid grid-cols-4 gap-2">
          <NSkeleton v-for="swatch in 4" :key="swatch" :sharp="false" height="32px" width="100%" />
        </div>
      </div>
    </div>

    <div v-else class="grid gap-3">
      <button
        v-for="theme in themes"
        :key="theme.id"
        class="group rounded-[var(--radius-xl)] border p-4 text-left transition duration-250"
        :class="
          isActiveTheme(theme)
            ? 'border-[color:var(--app-border-strong)] bg-[rgba(255,250,242,0.88)] shadow-[var(--shadow-hover)]'
            : 'border-[color:var(--app-border-subtle)] bg-[rgba(255,255,255,0.7)] hover:-translate-y-0.5 hover:border-[color:var(--app-border-strong)] hover:shadow-[var(--shadow-soft)]'
        "
        type="button"
        @click="applyTheme(theme)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <div class="text-sm font-semibold text-[color:var(--app-text)]">{{ theme.label }}</div>
              <NTag :bordered="false" round size="small" type="default">
                {{ resolveAppearanceLabel(theme) }}
              </NTag>
            </div>
            <div class="mt-2 text-xs text-[color:var(--app-text-tertiary)]">{{ theme.id }}</div>
          </div>
          <div
            class="rounded-full px-3 py-1 text-xs font-medium"
            :class="
              isApplyingTheme(theme)
                ? 'bg-[color:var(--app-primary-soft)] text-[color:var(--primary-300)]'
                : isActiveTheme(theme)
                  ? 'bg-[rgba(104,166,125,0.16)] text-[color:var(--primary-300)]'
                  : 'bg-[rgba(95,95,95,0.08)] text-[color:var(--app-text-secondary)]'
            "
          >
            {{ isApplyingTheme(theme) ? '应用中...' : isActiveTheme(theme) ? '当前主题' : '点击应用' }}
          </div>
        </div>

        <p class="mt-3 text-sm leading-6 text-[color:var(--app-text-secondary)]">
          {{ theme.description }}
        </p>

        <div class="mt-4 grid grid-cols-4 gap-2">
          <span
            class="h-9 rounded-[14px] border border-[rgba(255,255,255,0.3)] shadow-[inset_0_1px_0_rgba(255,255,255,0.25)]"
            :style="{ background: theme.colors.background }"
          />
          <span
            class="h-9 rounded-[14px] border border-[rgba(255,255,255,0.3)] shadow-[inset_0_1px_0_rgba(255,255,255,0.25)]"
            :style="{ background: theme.colors.surfaceStrong }"
          />
          <span
            class="h-9 rounded-[14px] border border-[rgba(255,255,255,0.3)] shadow-[inset_0_1px_0_rgba(255,255,255,0.25)]"
            :style="{ background: theme.colors.primary }"
          />
          <span
            class="h-9 rounded-[14px] border border-[rgba(255,255,255,0.3)] shadow-[inset_0_1px_0_rgba(255,255,255,0.25)]"
            :style="{ background: theme.colors.accent }"
          />
        </div>

        <div class="mt-4 flex items-center justify-between gap-3 text-xs text-[color:var(--app-text-tertiary)]">
          <span>动效风格 · {{ resolveAnimationLabel(theme.animationStyle) }}</span>
          <span>圆角 · {{ theme.borderRadius.lg }}</span>
        </div>
      </button>
    </div>
  </section>
</template>
