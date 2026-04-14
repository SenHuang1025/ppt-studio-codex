declare module 'vue' {
  export interface GlobalComponents {
    AnimatedChart: typeof import('./components/index')['AnimatedChart']
    CountUp: typeof import('./components/index')['CountUp']
    DataTable: typeof import('./components/index')['DataTable']
    IconCard: typeof import('./components/index')['IconCard']
    ProgressBar: typeof import('./components/index')['ProgressBar']
  }
}

export {}
