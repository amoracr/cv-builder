<template>
  <div class="job-dashboard">
    <header class="header">
      <h1>Job Automation Pipeline</h1>

      <!-- Contenedor que agrupa los filtros y botones -->
      <div class="header-actions">
        <!-- Selector de Filtro por Estado -->
        <select v-model="selectedStatus" class="status-filter">
          <option value="">Todos los estados</option>
          <option value="discovered">Discovered</option>
          <option value="to_apply">To Apply</option>
          <option value="applied">Applied</option>
          <option value="waiting">Waiting</option>
          <option value="interviewing">Interviewing</option>
          <option value="offered">Offered</option>
          <option value="manual_review">Manual Review</option>
          <option value="rejected">Rejected</option>
          <option value="ghosted">Ghosted</option>
          <option value="discarded">Discarded</option>
          <option value="hired">Hired</option>
        </select>

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

    <div v-else-if="filteredJobs.length === 0" class="loading">
      No hay ofertas que coincidan con el estado seleccionado.
    </div>

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
          <!-- Usamos filteredJobs en lugar de jobs -->
          <tr v-for="job in filteredJobs" :key="job.id">
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const jobs = ref([])
const loading = ref(false)
const scraping = ref(false)
const analyzing = ref(false)
const selectedStatus = ref('') // Variable reactiva para el filtro por estado

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

// Propiedad computada para filtrar dinámicamente las ofertas
const filteredJobs = computed(() => {
  if (!selectedStatus.value) return jobs.value
  return jobs.value.filter(job => job.status === selectedStatus.value)
})

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
      await fetchJobs()
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

/* Estilo para el selector de estado en la cabecera */
.status-filter {
  padding: 8px 12px;
  background: #fff;
  border: 1px solid $border-color;
  border-radius: 6px;
  color: $text-main;
  font-size: 0.9rem;
  font-family: inherit;
  cursor: pointer;
  outline: none;

  &:focus {
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.1);
  }
}
</style>