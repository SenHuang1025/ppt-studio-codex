import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { registerPreviewComponents } from './components/index'
import './theme/variables.css'

const app = createApp(App)

registerPreviewComponents(app)
app.use(router)
app.mount('#app')
