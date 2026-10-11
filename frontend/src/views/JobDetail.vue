<template>
  <div class="job-detail-container">
    <div v-if="loading" class="loading">Cargando detalle de la oferta...</div>

    <div v-else-if="job" class="job-detail-card">
      <header class="detail-header">
        <div class="header-titles">
          <span :class="['badge', job.status]">{{ job.status }}</span>
          <h1>{{ job.title }}</h1>
          <h2>{{ job.company?.name || 'Empresa confidencial' }}</h2>

          <div class="job-metadata-dates">
            <span>Creada: {{ formatDate(job.created_at) }}</span>
            <span v-if="job.updated_at"> • Actualizada: {{ formatDate(job.updated_at) }}</span>
          </div>
        </div>

        <div class="header-actions">
          <a :href="job.url" target="_blank" class="btn-external">Ver oferta original ↗</a>

          <!-- Botones para alternar entre formularios -->
          <button v-if="!isJobClosed" @click="toggleForm('status')" class="btn-toggle-status">
            {{ showStatusForm ? 'Cerrar form estado' : '✏️ Cambiar Estado' }}
          </button>

          <button v-if="!isJobClosed" @click="toggleForm('email')" class="btn-register-email">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
              <polyline points="22,6 12,13 2,6"></polyline>
            </svg>
            <span>{{ showEmailForm ? 'Cerrar form correo' : '✉️ Registrar Correo' }}</span>
          </button>
        </div>
      </header>

      <!-- FORMULARIO 1: Solo para cambiar el estado -->
      <div v-if="showStatusForm && !isJobClosed" class="form-section">
        <h3>Actualizar Estado de la Oferta</h3>
        <form @submit.prevent="submitStatusForm" class="action-form">
          <div class="form-group">
            <label>Nuevo Estado:</label>
            <select v-model="statusForm.status" class="form-control" required>
              <option value="discovered">Discovered</option>
              <option value="manual_review">Manual Review</option>
              <option value="to_apply">To Apply</option>
              <option value="applied">Applied</option>
              <option value="waiting">Waiting</option>
              <option value="interviewing">Interviewing</option>
              <option value="offered">Offered</option>
              <option value="discarded">Discarded</option>
              <option value="rejected">Rejected</option>
              <option value="ghosted">Ghosted</option>
              <option value="hired">Hired</option>
            </select>
          </div>
          <button type="submit" class="btn-submit" :disabled="submittingStatus">
            {{ submittingStatus ? 'Guardando...' : 'Guardar Nuevo Estado' }}
          </button>
        </form>
      </div>

      <!-- FORMULARIO 2: Para registrar correo y actualizar estado simultáneamente -->
      <div v-if="showEmailForm && !isJobClosed" class="form-section">
        <h3>Registrar Respuesta de Correo</h3>
        <form @submit.prevent="submitEmailForm" class="action-form">

          <div class="form-group">
            <label>Asunto del Correo:</label>
            <input v-model="emailForm.subject" type="text" class="form-control"
              placeholder="Ej. Update on Your Application Process" required />
          </div>

          <div class="form-group">
            <label>Remitente:</label>
            <input v-model="emailForm.sender" type="text" class="form-control"
              placeholder="Ej. Recruiter <recruiter@company.com>" required />
          </div>

          <div class="form-group">
            <label>Contenido del Correo:</label>
            <textarea v-model="emailForm.content" rows="5" class="form-control"
              placeholder="Pega el texto del correo aquí..." required></textarea>
          </div>

          <button type="submit" class="btn-submit" :disabled="submittingEmail">
            {{ submittingEmail ? 'Guardando...' : 'Guardar Correo y Actualizar' }}
          </button>
        </form>
      </div>

      <!-- Secciones de Contenido -->
      <div class="section">
        <h3>Análisis de IA (Match: {{ job.match_percentage }}%)</h3>
        <p class="reasoning">{{ job.ai_reasoning || 'Sin análisis previo.' }}</p>
      </div>

      <div class="section">
        <h3>Descripción del Puesto</h3>
        <div class="description-box" v-html="job.description || 'Sin descripción detallada.'"></div>
      </div>

      <div class="section emails-section">
        <h3>Historial de Correos Recibidos ({{ job.emails?.length || 0 }})</h3>

        <div v-if="job.emails && job.emails.length > 0" class="emails-list">
          <div v-for="email in job.emails" :key="email.id" class="email-item">
            <div class="email-meta">
              <strong>Asunto:</strong> {{ email.subject }} |
              <strong>De:</strong> {{ email.sender }}
              <span class="email-date">({{ formatDate(email.received_at) }})</span>
            </div>
            <div class="email-content">{{ email.content }}</div>
          </div>
        </div>
        <p v-else class="text-muted">Aún no hay correos registrados para esta oferta.</p>
      </div>

      <div class="footer-actions">
        <button @click="goBack" class="btn-back">← Volver a la lista</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const jobId = Number(route.params.id)

const job = ref(null)
const loading = ref(false)
const submittingStatus = ref(false)
const submittingEmail = ref(false)

// Control de visibilidad independiente para cada formulario
const showStatusForm = ref(false)
const showEmailForm = ref(false)

const statusForm = ref({
  status: ''
})

const emailForm = ref({
  subject: '',
  sender: '',
  content: ''
})

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const isJobClosed = computed(() => {
  if (!job.value || !job.value.status) return false
  const currentStatus = String(job.value.status).trim().toLowerCase()
  return ['rejected', 'ghosted', 'discarded', 'hired'].includes(currentStatus)
})

const fetchJobDetail = async () => {
  loading.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}`)
    if (response.ok) {
      job.value = await response.json()
      statusForm.value.status = job.value.status

      if (isJobClosed.value) {
        showStatusForm.value = false
        showEmailForm.value = false
      }
    }
  } catch (error) {
    console.error('Error al cargar el detalle de la oferta:', error)
  } finally {
    loading.value = false
  }
}

// Alternar formularios de forma exclusiva
const toggleForm = (formType) => {
  if (formType === 'status') {
    showStatusForm.value = !showStatusForm.value
    if (showStatusForm.value) showEmailForm.value = false
  } else {
    showEmailForm.value = !showEmailForm.value
    if (showEmailForm.value) showStatusForm.value = false
  }
}

// Enviar formulario exclusivo de cambio de estado
const submitStatusForm = async () => {
  submittingStatus.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}/status`, {
      method: 'PATCH', // O PUT según configures tu backend
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: statusForm.value.status })
    })

    if (response.ok) {
      showStatusForm.value = false
      await fetchJobDetail()
    } else {
      console.error('Error al actualizar el estado')
    }
  } catch (error) {
    console.error('Error de red:', error)
  } finally {
    submittingStatus.value = false
  }
}

// Enviar formulario de registro de correo
const submitEmailForm = async () => {
  submittingEmail.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}/register-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(emailForm.value)
    })

    if (response.ok) {
      showEmailForm.value = false
      await fetchJobDetail()
    } else {
      console.error('Error al registrar el correo')
    }
  } catch (error) {
    console.error('Error de red:', error)
  } finally {
    submittingEmail.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const goBack = () => {
  router.push({ name: 'JobIndex' })
}

onMounted(() => {
  fetchJobDetail()
})
</script>