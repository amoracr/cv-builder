<template>
  <div class="job-dashboard">
    <header class="header">
      <h1>Job Automation Pipeline</h1>

      <!-- Contenedor que agrupa los botones -->
      <div class="header-actions">
        <button @click="fetchJobs" class="btn-refresh">Actualizar Lista</button>
        <button @click="triggerScraping" class="btn-scrap" :disabled="scraping">
          {{ scraping ? 'Ejecutando scraping...' : '⚡ Buscar Nuevas Ofertas' }}
        </button>
        <button @click="triggerAnalyze" class="btn-analyze" :disabled="analyzing">
          {{ analyzing ? 'Analizando con IA...' : '🤖 Analizar Ofertas Descubiertas' }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading">Cargando ofertas...</div>

    <div v-else class="table-container">
      <table class="job-table">
        <thead>
          <tr>
            <th>Empresa</th>
            <th>Puesto</th>
            <th>Estado</th>
            <th>Actualización</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id">
            <td><strong>{{ job.company?.name || 'N/A' }}</strong></td>
            <td>
              <a href="#" @click.prevent="viewDetail(job.id)" class="job-title-link">
                {{ job.title }}
              </a>
            </td>
            <td>
              <span :class="['badge', job.status]">{{ job.status }}</span>
            </td>
            <td>{{ formatDate(job.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const jobs = ref([])
const loading = ref(false)
const scraping = ref(false) // <--- Asegúrate de tener esta línea declarada aquí
const analyzing = ref(false) // Estado de carga para el botón de análisis

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const fetchJobs = async () => {
  loading.value = true
  try {
    const response = await fetch(`${API_URL}/jobs`)
    if (response.ok) {
      jobs.value = await response.json()
    }
  } catch (error) {
    console.error('Error al cargar las ofertas:', error)
  } finally {
    loading.value = false
  }
}

const triggerScraping = async () => {
  scraping.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/scrap-offers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const result = await response.json()
      console.log('Scraping finalizado con éxito:', result)
      await fetchJobs()
    } else {
      console.error('Error al ejecutar el scraping en el servidor')
    }
  } catch (error) {
    console.error('Error de red al intentar hacer scraping:', error)
  } finally {
    scraping.value = false
  }
}

// Función para llamar al endpoint de análisis por IA
const triggerAnalyze = async () => {
  analyzing.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/analyze-offers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const result = await response.json()
      console.log('Análisis finalizado con éxito:', result)
      await fetchJobs() // Recarga la lista para reflejar los porcentajes de match o cambios
    } else {
      console.error('Error al ejecutar el análisis en el servidor')
    }
  } catch (error) {
    console.error('Error de red al intentar analizar las ofertas:', error)
  } finally {
    analyzing.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const viewDetail = (id) => {
  router.push({ name: 'JobDetail', params: { id } })
}

onMounted(() => {
  fetchJobs()
})
</script>

<style lang="scss">
.job-title-link {
  color: $primary-color;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}
</style>