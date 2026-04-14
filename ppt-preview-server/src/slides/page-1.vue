<script setup lang="ts">
import type { EChartsOption } from 'echarts'

type OverviewCard = {
  icon: string
  label: string
  trend: string
  value: string
}

type InitiativeProgress = {
  color: string
  label: string
  value: number
}

const overviewCards: OverviewCard[] = [
  {
    icon: '💼',
    label: 'Enterprise renewal mix stayed above plan and lifted overall revenue quality.',
    trend: '+14.2% QoQ',
    value: '$18.6M'
  },
  {
    icon: '🤝',
    label: 'Strategic account wins expanded into healthcare, retail, and advanced manufacturing.',
    trend: '+18 key wins',
    value: '126'
  },
  {
    icon: '🙂',
    label: 'Customer sentiment improved as onboarding time fell below three weeks.',
    trend: '+6 pts',
    value: '68'
  }
]

const initiatives: InitiativeProgress[] = [
  {
    color: 'var(--slide-primary)',
    label: 'Enterprise pipeline conversion',
    value: 82
  },
  {
    color: 'var(--slide-secondary)',
    label: 'Delivery margin recovery',
    value: 76
  },
  {
    color: 'var(--slide-accent)',
    label: 'Renewal expansion motion',
    value: 91
  }
]

const revenueMomentumOption: EChartsOption = {
  legend: {
    top: 0,
    itemGap: 20
  },
  tooltip: {
    trigger: 'axis'
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
  },
  yAxis: {
    type: 'value',
    splitNumber: 4
  },
  series: [
    {
      name: 'Pipeline coverage',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 10,
      data: [2.6, 2.8, 2.9, 3.2, 3.4, 3.7],
      lineStyle: {
        width: 4
      },
      areaStyle: {
        opacity: 0.18
      }
    },
    {
      name: 'Closed revenue',
      type: 'bar',
      barWidth: 30,
      data: [8.2, 8.9, 9.4, 10.6, 11.4, 12.1]
    }
  ]
}
</script>

<template>
  <main class="slide-page">
    <section class="hero-grid">
      <article class="hero-copy panel">
        <div class="eyebrow">2026 Q1 operating review</div>
        <h1>Warm-paper executive overview with reusable preview primitives</h1>
        <p class="subtitle">
          This sample slide validates the upgraded preview sandbox: reusable KPI cards, animated number
          rollup, progress tracks, and a themed chart all render inside the 1920×1080 canvas.
        </p>
        <div class="hero-tags">
          <span class="hero-tag">Preview service managed by Electron</span>
          <span class="hero-tag">Base components registered globally</span>
        </div>
      </article>

      <aside class="spotlight panel">
        <div class="eyebrow">Revenue headline</div>
        <div class="spotlight-value">
          <CountUp :decimals="1" :duration="2.1" :end="18.6" prefix="$" suffix="M" />
        </div>
        <div class="spotlight-copy">
          Closed quarter revenue came in above plan, with expansion-led renewals taking a larger share of
          the mix.
        </div>
        <div class="spotlight-meta">
          <div>
            <span class="spotlight-meta__label">Operating margin</span>
            <span class="spotlight-meta__value">24.8%</span>
          </div>
          <div>
            <span class="spotlight-meta__label">Forecast confidence</span>
            <span class="spotlight-meta__value">High</span>
          </div>
        </div>
      </aside>
    </section>

    <section class="metrics-grid">
      <IconCard
        v-for="card in overviewCards"
        :key="card.label"
        :icon="card.icon"
        :label="card.label"
        :trend="card.trend"
        :value="card.value"
      />
    </section>

    <section class="content-grid">
      <article class="panel execution-panel">
        <div class="section-head">
          <div>
            <div class="eyebrow">Execution snapshot</div>
            <h2>Three workstreams now shaping the quarter</h2>
          </div>
          <div class="section-pill">Progress</div>
        </div>

        <div class="progress-list">
          <ProgressBar
            v-for="initiative in initiatives"
            :key="initiative.label"
            :animated="true"
            :color="initiative.color"
            :label="initiative.label"
            :value="initiative.value"
          />
        </div>

        <div class="bullet-list">
          <div class="bullet-item">Expansion plays are now concentrated on accounts with active product champions.</div>
          <div class="bullet-item">Implementation risk is declining as onboarding templates standardize across regions.</div>
          <div class="bullet-item">The next priority is turning strong close rates into repeatable cross-sell motion.</div>
        </div>
      </article>

      <article class="panel chart-panel">
        <div class="section-head">
          <div>
            <div class="eyebrow">Momentum view</div>
            <h2>Coverage and closed revenue are rising in parallel</h2>
          </div>
          <div class="section-pill section-pill--accent">Animated chart</div>
        </div>

        <AnimatedChart :animation-delay="120" :option="revenueMomentumOption" />
      </article>
    </section>
  </main>
</template>

<style scoped>
.slide-page {
  position: relative;
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 26px;
  padding: 62px 76px 56px;
  background:
    radial-gradient(circle at top left, var(--slide-secondary-soft) 0%, transparent 36%),
    radial-gradient(circle at 84% 16%, var(--slide-accent-soft) 0%, transparent 24%),
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--slide-bg) 84%, var(--slide-surface-strong) 16%) 0%,
      var(--slide-bg) 56%,
      color-mix(in srgb, var(--slide-surface) 68%, var(--slide-bg) 32%) 100%
    );
  color: var(--slide-text);
  font-family: var(--slide-font-body);
}

.slide-page::before {
  content: '';
  position: absolute;
  inset: 22px;
  border: 1px solid color-mix(in srgb, var(--slide-border) 52%, transparent);
  border-radius: 34px;
  pointer-events: none;
}

.panel {
  border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
  border-radius: var(--slide-radius-xl);
  background: var(--slide-surface-strong);
  box-shadow: var(--slide-shadow-soft);
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.24fr) minmax(380px, 0.76fr);
  gap: 24px;
}

.hero-copy {
  padding: 38px 42px 34px;
}

.eyebrow {
  margin-bottom: 14px;
  color: var(--slide-text-secondary);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.hero-copy h1,
.section-head h2 {
  margin: 0;
  font-family: var(--slide-font-title);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.hero-copy h1 {
  max-width: 1040px;
  font-size: 62px;
}

.subtitle {
  margin: 18px 0 0;
  max-width: 1040px;
  color: var(--slide-text-secondary);
  font-size: 23px;
  line-height: 1.72;
}

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.hero-tag,
.section-pill {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  background: var(--slide-primary-soft);
  color: var(--slide-primary);
  font-size: 14px;
  font-weight: 700;
}

.section-pill--accent {
  background: var(--slide-accent-soft);
  color: var(--slide-accent);
}

.spotlight {
  display: grid;
  align-content: start;
  gap: 18px;
  padding: 30px 32px;
  background: linear-gradient(
    180deg,
    var(--slide-surface-soft) 0%,
    color-mix(in srgb, var(--slide-bg) 72%, var(--slide-surface-soft) 28%) 100%
  );
}

.spotlight-value {
  font-family: var(--slide-font-title);
  font-size: 82px;
  line-height: 0.95;
  letter-spacing: -0.05em;
}

.spotlight-copy {
  color: var(--slide-text-secondary);
  font-size: 21px;
  line-height: 1.7;
}

.spotlight-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.spotlight-meta > div {
  display: grid;
  gap: 6px;
  padding: 18px 18px 16px;
  border-radius: 20px;
  background: var(--slide-surface-strong);
}

.spotlight-meta__label {
  color: var(--slide-text-secondary);
  font-size: 14px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.spotlight-meta__value {
  font-family: var(--slide-font-title);
  font-size: 28px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.96fr);
  gap: 24px;
}

.execution-panel,
.chart-panel {
  display: grid;
  gap: 24px;
  padding: 30px 32px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.section-head h2 {
  font-size: 34px;
}

.progress-list {
  display: grid;
  gap: 18px;
}

.bullet-list {
  display: grid;
  gap: 14px;
  margin-top: auto;
}

.bullet-item {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  color: var(--slide-text-secondary);
  font-size: 18px;
  line-height: 1.72;
}

.bullet-item::before {
  content: '';
  width: 12px;
  height: 12px;
  margin-top: 9px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--slide-primary) 0%, var(--slide-accent) 100%);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--slide-primary) 10%, transparent);
}
</style>
