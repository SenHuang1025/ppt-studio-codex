<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import { BarChart, LineChart, PieChart, RadarChart, ScatterChart } from 'echarts/charts'
import { DatasetComponent, GridComponent, LegendComponent, TitleComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([
  BarChart,
  CanvasRenderer,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  LineChart,
  PieChart,
  RadarChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent
])

interface Props {
  option?: EChartsOption
  animationDelay?: number
}

type ThemeTokens = {
  accent: string
  border: string
  gridLine: string
  primary: string
  secondary: string
  surface: string
  text: string
  textSecondary: string
}

const props = withDefaults(defineProps<Props>(), {
  animationDelay: 0
})

const chartRef = ref<InstanceType<typeof VChart> | null>(null)
const themeVersion = ref(0)
let themeObserver: MutationObserver | null = null

const resolvedOption = computed<EChartsOption>(() => {
  themeVersion.value
  const tokens = readThemeTokens()
  const baseOption = props.option ?? createFallbackOption(tokens)

  return {
    ...baseOption,
    backgroundColor: baseOption.backgroundColor ?? 'transparent',
    animation: baseOption.animation ?? true,
    animationDuration: baseOption.animationDuration ?? 900,
    animationEasing: baseOption.animationEasing ?? 'cubicOut',
    color: baseOption.color ?? [tokens.primary, tokens.secondary, tokens.accent, tokens.textSecondary, tokens.border],
    textStyle: {
      color: tokens.text,
      fontFamily: 'var(--slide-font-body)',
      ...toRecord(baseOption.textStyle)
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: tokens.surface,
      borderColor: tokens.border,
      borderWidth: 1,
      textStyle: {
        color: tokens.text,
        fontFamily: 'var(--slide-font-body)'
      },
      extraCssText: 'border-radius: 18px; box-shadow: var(--slide-shadow-soft);',
      ...toRecord(baseOption.tooltip)
    },
    grid: {
      top: 44,
      right: 24,
      bottom: 28,
      left: 44,
      containLabel: true,
      ...toRecord(baseOption.grid)
    },
    series: resolveSeries(baseOption.series, props.animationDelay)
  }
})

const chartTheme = computed<Record<string, unknown>>(() => {
  themeVersion.value
  const tokens = readThemeTokens()

  return {
    color: [tokens.primary, tokens.secondary, tokens.accent, tokens.textSecondary, tokens.border],
    backgroundColor: 'transparent',
    textStyle: {
      color: tokens.text,
      fontFamily: 'var(--slide-font-body)'
    },
    title: {
      textStyle: {
        color: tokens.text,
        fontFamily: 'var(--slide-font-title)'
      },
      subtextStyle: {
        color: tokens.textSecondary
      }
    },
    legend: {
      textStyle: {
        color: tokens.textSecondary
      }
    },
    tooltip: {
      backgroundColor: tokens.surface,
      borderColor: tokens.border,
      textStyle: {
        color: tokens.text
      }
    },
    categoryAxis: {
      axisLine: {
        lineStyle: {
          color: tokens.border
        }
      },
      axisTick: {
        lineStyle: {
          color: tokens.border
        }
      },
      axisLabel: {
        color: tokens.textSecondary
      },
      splitLine: {
        lineStyle: {
          color: tokens.gridLine
        }
      }
    },
    valueAxis: {
      axisLine: {
        lineStyle: {
          color: tokens.border
        }
      },
      axisLabel: {
        color: tokens.textSecondary
      },
      splitLine: {
        lineStyle: {
          color: tokens.gridLine
        }
      }
    }
  }
})

onMounted(() => {
  if (typeof window === 'undefined' || typeof MutationObserver === 'undefined') {
    return
  }

  themeObserver = new MutationObserver(() => {
    themeVersion.value += 1
  })

  themeObserver.observe(document.head, {
    attributes: true,
    characterData: true,
    childList: true,
    subtree: true
  })
  themeObserver.observe(document.documentElement, {
    attributeFilter: ['class', 'style'],
    attributes: true
  })
})

onBeforeUnmount(() => {
  themeObserver?.disconnect()
  chartRef.value?.dispose()
})

function createFallbackOption(tokens: ThemeTokens): EChartsOption {
  return {
    legend: {
      top: 0,
      icon: 'circle'
    },
    xAxis: {
      type: 'category',
      data: ['North', 'East', 'South', 'West']
    },
    yAxis: {
      type: 'value',
      splitNumber: 4
    },
    series: [
      {
        type: 'bar',
        barWidth: 34,
        data: [72, 88, 64, 91],
        itemStyle: {
          color: tokens.primary
        }
      }
    ]
  }
}

function resolveSeries(series: EChartsOption['series'], animationDelay: number): EChartsOption['series'] {
  const seriesEntries = Array.isArray(series) ? series : series ? [series] : []

  return seriesEntries.map((entry, index) => {
    const normalizedEntry = toRecord(entry)
    const seriesType = typeof normalizedEntry.type === 'string' ? normalizedEntry.type : ''

    return {
      animation: true,
      animationDuration: 900,
      animationEasing: 'cubicOut',
      animationDelay: animationDelay + index * 120,
      ...normalizedEntry,
      itemStyle:
        seriesType === 'bar'
          ? {
              borderRadius: [18, 18, 6, 6],
              ...toRecord(normalizedEntry.itemStyle)
            }
          : normalizedEntry.itemStyle
    }
  }) as EChartsOption['series']
}

function readThemeTokens(): ThemeTokens {
  if (typeof window === 'undefined') {
    return {
      accent: '#f18f01',
      border: '#c2baa6',
      gridLine: 'rgba(131, 53, 0, 0.08)',
      primary: '#68a67d',
      secondary: '#8fbf9f',
      surface: 'rgba(255, 251, 243, 0.92)',
      text: '#353535',
      textSecondary: '#5f5f5f'
    }
  }

  const styles = window.getComputedStyle(document.documentElement)

  return {
    accent: readCssVariable(styles, '--slide-accent', '#f18f01'),
    border: readCssVariable(styles, '--slide-border', '#c2baa6'),
    gridLine: readCssVariable(styles, '--slide-grid-line', 'rgba(131, 53, 0, 0.08)'),
    primary: readCssVariable(styles, '--slide-primary', '#68a67d'),
    secondary: readCssVariable(styles, '--slide-secondary', '#8fbf9f'),
    surface: readCssVariable(styles, '--slide-surface-strong', 'rgba(255, 251, 243, 0.92)'),
    text: readCssVariable(styles, '--slide-text', '#353535'),
    textSecondary: readCssVariable(styles, '--slide-text-secondary', '#5f5f5f')
  }
}

function readCssVariable(styles: CSSStyleDeclaration, name: string, fallback: string): string {
  const value = styles.getPropertyValue(name).trim()
  return value || fallback
}

function toRecord(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return {}
  }

  return value as Record<string, unknown>
}
</script>

<template>
  <div class="chart-shell">
    <VChart ref="chartRef" :option="resolvedOption" :theme="chartTheme" autoresize class="chart" />
  </div>
</template>

<style scoped>
.chart-shell {
  width: 100%;
  height: 100%;
  min-height: 300px;
  padding: 16px 18px 10px;
  border-radius: var(--slide-radius-lg);
  border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
  background: linear-gradient(180deg, var(--slide-surface-strong) 0%, var(--slide-surface-soft) 100%);
  box-shadow: var(--slide-shadow-soft);
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 274px;
}
</style>
