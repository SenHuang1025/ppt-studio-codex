import type { App, Component } from 'vue'
import AnimatedChart from './AnimatedChart.vue'
import CountUp from './CountUp.vue'
import DataTable from './DataTable.vue'
import IconCard from './IconCard.vue'
import ProgressBar from './ProgressBar.vue'

export { AnimatedChart, CountUp, DataTable, IconCard, ProgressBar }

const previewComponents: Record<string, Component> = {
  AnimatedChart,
  CountUp,
  DataTable,
  IconCard,
  ProgressBar
}

export function registerPreviewComponents(app: App): void {
  Object.entries(previewComponents).forEach(([name, component]) => {
    app.component(name, component)
  })
}
