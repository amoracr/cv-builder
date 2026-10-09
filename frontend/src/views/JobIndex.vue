<template>
  <div class="job-dashboard">
    <header class="header">
      <h1>Job Automation Pipeline</h1>
      <button @click="fetchJobs" class="btn-refresh">Actualizar Lista</button>
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
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id">
            <td><strong>{{ job.company?.name || 'N/A' }}</strong></td>
            <td>
              <a :href="job.url" target="_blank" class="job-title-link">{{ job.title }}</a>
            </td>
            <td>
              <span :class="['badge', job.status]">{{ job.status }}</span>
            </td>
            <td>{{ formatDate(job.updated_at) }}</td>
            <td>
              <div class="actions">
                <button @click="viewDetail(job.id)" class="btn-action">Detalle</button>
                <button @click="openAddEmailModal(job)" class="btn-action primary">+ Correo</button>
              </div>
            </td>
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

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const viewDetail = (id) => {
  router.push({ name: 'JobDetail', params: { id } })
}

const openAddEmailModal = (job) => {
  console.log(`Agregar correo para la oferta: ${job.title}`)
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