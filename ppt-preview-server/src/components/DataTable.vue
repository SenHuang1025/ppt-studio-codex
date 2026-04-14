<script setup lang="ts">
import { computed } from 'vue'

type ColumnAlign = 'left' | 'center' | 'right'

interface TableColumn {
  key: string
  title: string
  align?: ColumnAlign
  width?: string
}

type TableRow = Record<string, unknown>

interface Props {
  columns: TableColumn[]
  data: TableRow[]
  striped?: boolean
  animated?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  striped: true,
  animated: false
})

const columnCount = computed(() => Math.max(props.columns.length, 1))
const hasRows = computed(() => props.data.length > 0)

function resolveCellValue(row: TableRow, key: string): string {
  const value = row[key]

  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return String(value)
}

function resolveAlign(column: TableColumn): ColumnAlign {
  return column.align ?? 'left'
}
</script>

<template>
  <div class="table-shell">
    <table class="data-table">
      <thead>
        <tr>
          <th
            v-for="column in props.columns"
            :key="column.key"
            :style="{ textAlign: resolveAlign(column), width: column.width }"
          >
            {{ column.title }}
          </th>
        </tr>
      </thead>
      <tbody v-if="hasRows">
        <tr
          v-for="(row, rowIndex) in props.data"
          :key="rowIndex"
          :class="{
            'data-table__row--animated': animated,
            'data-table__row--striped': striped && rowIndex % 2 === 1
          }"
          :style="{ '--row-index': String(rowIndex) }"
        >
          <td
            v-for="column in props.columns"
            :key="column.key"
            :style="{ textAlign: resolveAlign(column) }"
          >
            {{ resolveCellValue(row, column.key) }}
          </td>
        </tr>
      </tbody>
      <tbody v-else>
        <tr>
          <td :colspan="columnCount" class="data-table__empty">No data available.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-shell {
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--slide-border) 78%, transparent);
  border-radius: var(--slide-radius-lg);
  background: linear-gradient(180deg, var(--slide-surface-strong) 0%, var(--slide-surface-soft) 100%);
  box-shadow: var(--slide-shadow-soft);
}

.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

thead th {
  padding: 20px 22px;
  background: var(--slide-secondary-soft);
  color: var(--slide-text);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

tbody td {
  padding: 18px 22px;
  border-top: 1px solid color-mix(in srgb, var(--slide-border) 62%, transparent);
  color: var(--slide-text);
  font-size: 15px;
  line-height: 1.6;
}

.data-table__row--striped {
  background: color-mix(in srgb, var(--slide-surface-soft) 88%, transparent);
}

.data-table__row--animated {
  opacity: 0;
  transform: translateY(10px);
  animation: row-reveal 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: calc(var(--row-index) * 85ms);
}

.data-table__empty {
  padding: 30px 22px;
  text-align: center;
  color: var(--slide-text-secondary);
}

@keyframes row-reveal {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
