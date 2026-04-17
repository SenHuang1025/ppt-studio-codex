import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router'
import { installErrorHandling, reportGlobalError } from '@/services/errorHandling'
import 'uno.css'
import '@/assets/styles/base.css'

const app = createApp(App)

installErrorHandling({ router })

app.config.errorHandler = (error, _instance, info) => {
  reportGlobalError(error, {
    context: `vue.errorHandler:${info}`,
    notify: true
  })
}

app.use(createPinia())
app.use(router)
app.mount('#app')
