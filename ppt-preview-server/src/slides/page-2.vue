<script setup lang="ts">
type ColumnAlign = 'left' | 'center' | 'right'

type TableColumn = {
  align?: ColumnAlign
  key: string
  title: string
  width?: string
}

type PriorityRow = {
  account: string
  growth: string
  health: string
  priority: string
  region: string
}

type DeliveryFocus = {
  color: string
  label: string
  value: number
}

const priorityColumns: TableColumn[] = [
  {
    key: 'account',
    title: 'Account',
    width: '28%'
  },
  {
    key: 'region',
    title: 'Region',
    width: '16%'
  },
  {
    align: 'right',
    key: 'growth',
    title: 'Growth'
  },
  {
    key: 'health',
    title: 'Health'
  },
  {
    key: 'priority',
    title: 'Priority'
  }
]

const priorityRows: PriorityRow[] = [
  {
    account: 'Northwind Health',
    growth: '+26%',
    health: 'On track',
    priority: 'Expand analytics scope',
    region: 'NA'
  },
  {
    account: 'Blue Harbor Retail',
    growth: '+18%',
    health: 'Watch list',
    priority: 'Stabilize rollout pace',
    region: 'EU'
  },
  {
    account: 'Nova Components',
    growth: '+31%',
    health: 'On track',
    priority: 'Lock executive sponsor',
    region: 'APAC'
  },
  {
    account: 'Summit Logistics',
    growth: '+22%',
    health: 'At risk',
    priority: 'Recover onboarding timeline',
    region: 'NA'
  }
]

const deliveryFocus: DeliveryFocus[] = [
  {
    color: 'var(--slide-primary)',
    label: 'Sponsor alignment',
    value: 88
  },
  {
    color: 'var(--slide-secondary)',
    label: 'Implementation readiness',
    value: 79
  },
  {
    color: 'var(--slide-accent)',
    label: 'Renewal whitespace coverage',
    value: 93
  }
]
</script>

<template>
  <main class="slide-page">
    <section class="hero-grid">
      <article class="hero panel">
        <div class="eyebrow">Priority accounts</div>
        <h1>Account heatmap for the next wave of expansion work</h1>
        <p>
          The second sample page focuses on tabular presentation. It verifies that the preview sandbox can
          render a PPT-style data table without falling back to admin-dashboard visuals.
        </p>
      </article>

      <aside class="summary panel">
        <div class="eyebrow">Coverage</div>
        <div class="summary-value">
          <CountUp :duration="1.8" :end="92" suffix="%" />
        </div>
        <div class="summary-copy">Top-tier accounts now have clear owners, next actions, and risk flags.</div>
      </aside>
    </section>

    <section class="content-grid">
      <article class="panel table-panel">
        <div class="panel-head">
          <div>
            <div class="eyebrow">This quarter</div>
            <h2>Priority account table</h2>
          </div>
          <div class="panel-pill">Data table</div>
        </div>

        <DataTable :animated="true" :columns="priorityColumns" :data="priorityRows" :striped="true" />
      </article>

      <article class="panel focus-panel">
        <div class="panel-head">
          <div>
            <div class="eyebrow">Delivery focus</div>
            <h2>Shortlist for weekly review</h2>
          </div>
        </div>

        <div class="focus-list">
          <ProgressBar
            v-for="item in deliveryFocus"
            :key="item.label"
            :animated="true"
            :color="item.color"
            :label="item.label"
            :value="item.value"
          />
        </div>

        <div class="note-card">
          <div class="note-card__title">Working rule</div>
          <p>Any account below implementation-readiness 80% stays out of expansion packaging until delivery risk drops.</p>
        </div>
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
  grid-template-rows: auto 1fr;
  gap: 28px;
  padding: 64px 76px 58px;
  background:
    radial-gradient(circle at top left, var(--slide-secondary-soft) 0%, transparent 34%),
    radial-gradient(circle at 88% 14%, var(--slide-accent-soft) 0%, transparent 22%),
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
  grid-template-columns: minmax(0, 1.22fr) minmax(360px, 0.78fr);
  gap: 24px;
}

.hero,
.summary,
.table-panel,
.focus-panel {
  padding: 32px 34px;
}

.hero h1,
.panel-head h2 {
  margin: 0;
  font-family: var(--slide-font-title);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.hero h1 {
  font-size: 58px;
}

.hero p,
.summary-copy,
.note-card p {
  margin: 16px 0 0;
  color: var(--slide-text-secondary);
  font-size: 22px;
  line-height: 1.72;
}

.eyebrow {
  margin-bottom: 14px;
  color: var(--slide-text-secondary);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.summary {
  display: grid;
  align-content: start;
  gap: 14px;
  background: linear-gradient(
    180deg,
    var(--slide-surface-soft) 0%,
    color-mix(in srgb, var(--slide-bg) 72%, var(--slide-surface-soft) 28%) 100%
  );
}

.summary-value {
  font-family: var(--slide-font-title);
  font-size: 78px;
  line-height: 0.95;
  letter-spacing: -0.05em;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 24px;
}

.table-panel,
.focus-panel {
  display: grid;
  gap: 22px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-head h2 {
  font-size: 34px;
}

.panel-pill {
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

.focus-list {
  display: grid;
  gap: 18px;
}

.note-card {
  display: grid;
  gap: 8px;
  margin-top: auto;
  padding: 24px 26px;
  border-radius: 24px;
  background: var(--slide-surface-soft);
  border: 1px solid color-mix(in srgb, var(--slide-border) 68%, transparent);
}

.note-card__title {
  font-size: 18px;
  font-weight: 700;
}

.note-card p {
  margin-top: 0;
  font-size: 18px;
}
</style>
