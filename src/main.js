import './assets/main.css'

import axios from 'axios'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import VueKonva from 'vue-konva'
import App from './App.vue'

// 配置axios的baseURL
axios.defaults.baseURL = 'http://localhost:8000'

const pinia = createPinia()
const app = createApp(App)

app.use(VueKonva)
app.use(pinia)
app.mount('#app')
