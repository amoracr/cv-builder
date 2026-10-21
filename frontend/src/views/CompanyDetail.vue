<template>
  <div class="job-dashboard">
    <header class="header">
      <div class="header-left">
        <h1>{{ companyName ? `Puestos de ${companyName}` : 'Cargando empresa...' }}</h1>
      </div>
      <div class="header-actions">
        <router-link to="/" class="btn-refresh">Volver al Dashboard</router-link>
      </div>
    </header>

    <div v-if="loading" class="loading">Cargando información de la empresa...</div>

    <div v-else-if="jobs.length === 0" class="loading">
      No hay puestos registrados para esta empresa.
    </div>

    <div v-else class="table-container">
      <table class="job-table">
        <thead>
          <tr>
            <th>Puesto</th>
            <th>Estado</th>
            <th>Actualización</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id">
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
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const companyName = ref('')
const jobs = ref([])
const loading = ref(false)

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const fetchCompanyJobs = async () => {
  const companyId = route.params.id
  if (!companyId) return

  loading.value = true
  try {
    const response = await fetch(`${API_URL}/company/${companyId}/jobs`)
    if (response.ok) {
      const data = await response.json()
      companyName.value = data.company_name
      jobs.value = data.jobs || []
    } else {
      console.error('No se pudo encontrar la empresa.')
    }
  } catch (error) {
    console.error('Error de red al cargar los puestos de la empresa:', error)
  } finally {
    loading.value = false
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
  fetchCompanyJobs()
})
</script>

<style scoped lang="scss">
@use '@/styles/dashboard' as *; // Ajusta la ruta según la ubicación de tu archivo _dashboard.scss
</style>