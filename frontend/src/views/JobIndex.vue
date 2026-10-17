<template>
  <div class="job-dashboard">
    <header class="header">
      <div class="header-left">
        <h1>Job Automation Pipeline</h1>
      </div>

      <!-- Grupo derecho: Botones de acción -->
      <div class="header-actions">
        <router-link to="/jobs/add" class="btn-add">
          + Añadir Oferta
        </router-link>
        <button @click="refreshData" class="btn-refresh">Actualizar Lista</button>
        <button @click="triggerScraping" class="btn-scrap" :disabled="scraping">
          {{ scraping ? 'Ejecutando...' : '⚡ Buscar' }}
        </button>
        <button @click="triggerAnalyze" class="btn-analyze" :disabled="analyzing">
          {{ analyzing ? 'Analizando...' : '🤖 Analizar' }}
        </button>
        <button @click="triggerArchiveExpired" class="btn-archive" :disabled="archiving">
          {{ archiving ? 'Archivando...' : '📦 Archivar' }}
        </button>
      </div>
    </header>

    <!-- Contadores superiores y filtro de estados alimentados desde el backend -->
    <div class="status-counters-grid">
      <div class="counter-card" :class="{ active: selectedStatus === '' }" @click="filterByStatus('')">
        <span class="counter-title">Todas</span>
        <span class="counter-value">{{ totalJobsCount }}</span>
      </div>
      <div v-for="st in availableStatuses" :key="st.value" class="counter-card"
        :class="{ active: selectedStatus === st.value }" @click="filterByStatus(st.value)">
        <span class="counter-title">{{ st.label }}</span>
        <span class="counter-value">{{ statusCounts[st.value] || 0 }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading">Cargando ofertas...</div>

    <div v-else-if="jobs.length === 0" class="loading">
      No hay ofertas que coincidan con el estado seleccionado.
    </div>

    <div v-else>
      <div class="table-container">
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

      <!-- Controles de Paginación -->
      <div class="pagination-controls" v-if="totalPages > 1">
        <button @click="changePage(page - 1)" :disabled="page <= 1" class="btn-page">
          &laquo; Anterior
        </button>
        <span>Página {{ page }} de {{ totalPages }}</span>
        <button @click="changePage(page + 1)" :disabled="page >= totalPages" class="btn-page">
          Siguiente &raquo;
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const availableStatuses = ref([])
const statusCounts = ref({})
const jobs = ref([])

const loading = ref(false)
const scraping = ref(false)
const analyzing = ref(false)
const archiving = ref(false)

// Paginación y Filtro
const selectedStatus = ref('')
const page = ref(1)
const totalPages = ref(1)
const pageSize = 20

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

// Actualiza los query params en la URL sin recargar
const updateUrlParams = () => {
  const query = {}
  if (selectedStatus.value) query.status = selectedStatus.value
  if (page.value > 1) query.page = page.value

  router.replace({ name: 'JobIndex', query })
}

const fetchStatuses = async () => {
  try {
    const response = await fetch(`${API_URL}/jobs/statuses`)
    if (response.ok) {
      availableStatuses.value = await response.json()
    }
  } catch (error) {
    console.error('Error al cargar los estados:', error)
  }
}

const fetchCounts = async () => {
  try {
    const response = await fetch(`${API_URL}/jobs/counts`)
    if (response.ok) {
      const data = await response.json()
      const normalizedCounts = {}
      for (const [key, value] of Object.entries(data)) {
        normalizedCounts[key.toLowerCase()] = value
      }
      statusCounts.value = normalizedCounts
    }
  } catch (error) {
    console.error('Error al cargar los contadores de estado:', error)
  }
}

const totalJobsCount = computed(() => {
  return Object.values(statusCounts.value).reduce((a, b) => a + b, 0)
})

const fetchJobs = async () => {
  loading.value = true
  try {
    let url = `${API_URL}/jobs/?page=${page.value}&page_size=${pageSize}`
    if (selectedStatus.value) {
      url += `&status=${selectedStatus.value}`
    }

    const response = await fetch(url)
    if (response.ok) {
      const data = await response.json()
      jobs.value = data.jobs || []
      totalPages.value = data.total_pages || 1
    }
  } catch (error) {
    console.error('Error al cargar las ofertas:', error)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await Promise.all([fetchCounts(), fetchJobs()])
}

const filterByStatus = (status) => {
  selectedStatus.value = status
  page.value = 1
  updateUrlParams()
  fetchJobs()
}

const changePage = (newPage) => {
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    updateUrlParams()
    fetchJobs()
  }
}

const triggerScraping = async () => {
  scraping.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/scrap-offers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    if (response.ok) {
      await refreshData()
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
      headers: { 'Content-Type': 'application/json' }
    })
    if (response.ok) {
      await refreshData()
    }
  } catch (error) {
    console.error('Error de red al intentar analizar las ofertas:', error)
  } finally {
    analyzing.value = false
  }
}

const triggerArchiveExpired = async () => {
  archiving.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/archive-expired`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    if (response.ok) {
      await refreshData()
    }
  } catch (error) {
    console.error('Error de red al intentar archivar las ofertas:', error)
  } finally {
    archiving.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const viewDetail = (id) => {
  router.push({
    name: 'JobDetail',
    params: { id },
    query: {
      ...(selectedStatus.value ? { status: selectedStatus.value } : {}),
      ...(page.value > 1 ? { page: page.value } : {})
    }
  })
}

onMounted(async () => {
  // 1. Recuperar estado y página desde la URL al cargar o regresar
  if (route.query.status !== undefined) {
    selectedStatus.value = String(route.query.status)
  }
  if (route.query.page) {
    page.value = parseInt(route.query.page, 10) || 1
  }

  // 2. Cargar datos
  await fetchStatuses()
  await fetchCounts()
  await fetchJobs()
})
</script>

<style scoped lang="scss">
@use '@/styles/dashboard' as *; // Ajusta la ruta según la ubicación de tu archivo _dashboard.scss
</style>