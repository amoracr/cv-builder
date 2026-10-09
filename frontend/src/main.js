import { createApp } from 'vue'
import App from './App.vue'
import router from './router' // Importa tu configuración de rutas

// Importa tus estilos globales o de SCSS
import './styles/main.scss' 

const app = createApp(App)

app.use(router) // Registra Vue Router
app.mount('#app')