import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(VueQueryPlugin)
app.mount('#app')
