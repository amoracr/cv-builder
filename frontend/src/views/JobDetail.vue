<template>
  <div class="job-detail-container">
    <div v-if="loading" class="loading">Cargando detalle de la oferta...</div>

    <div v-else-if="job" class="job-detail-card">
      <header class="detail-header">
        <div>
          <span :class="['badge', job.status]">{{ job.status }}</span>
          <h1>{{ job.title }}</h1>
          <h2>{{ job.company?.name || 'Empresa confidencial' }}</h2>
        </div>
        <div class="header-actions">
          <a :href="job.url" target="_blank" class="btn-external">Ver oferta original ↗</a>
          
          <!-- El botón solo se muestra si el trabajo NO está en un estado cerrado -->
          <button 
            v-if="!isJobClosed" 
            @click="toggleEmailForm" 
            class="btn-action primary"
          >
            {{ showEmailForm ? 'Cancelar' : '+ Registrar Correo / Estado' }}
          </button>
        </div>
      </header>

      <!-- Formulario para agregar correo y cambiar estado (también se oculta por seguridad si se cierra) -->
      <div v-if="showEmailForm && !isJobClosed" class="email-form-section">
        <h3>Registrar Respuesta de Correo</h3>
        <form @submit.prevent="submitEmailForm" class="email-form">
          <div class="form-group">
            <label>Nuevo Estado de la Oferta:</label>
            <select v-model="emailForm.status" class="form-control" required>
              <option value="discovered">Discovered</option>
              <option value="manual_review">Manual Review</option>
              <option value="to_apply">To Apply</option>
              <option value="applied">Applied</option>
              <option value="waiting">Waiting</option>
              <option value="interviewing">Interviewing</option>
              <option value="offered">Offered</option>
              <option value="discarded">Discarded (Rechazado)</option>
              <option value="rejected">Rejected</option>
              <option value="ghosted">Ghosted</option>
              <option value="hired">Hired</option>
            </select>
          </div>

          <div class="form-group">
            <label>Asunto del Correo:</label>
            <input v-model="emailForm.subject" type="text" class="form-control" placeholder="Ej. Update on Your Application Process" required />
          </div>

          <div class="form-group">
            <label>Remitente:</label>
            <input v-model="emailForm.sender" type="text" class="form-control" placeholder="Ej. Recruiter <recruiter@company.com>" required />
          </div>

          <div class="form-group">
            <label>Contenido del Correo:</label>
            <textarea v-model="emailForm.content" rows="5" class="form-control" placeholder="Pega el texto del correo aquí..." required></textarea>
          </div>

          <button type="submit" class="btn-submit" :disabled="submitting">
            {{ submitting ? 'Guardando...' : 'Guardar Correo y Actualizar Estado' }}
          </button>
        </form>
      </div>

      <!-- El resto de tus secciones (IA, Descripción, Historial de Correos, etc.) se mantienen igual -->
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
const submitting = ref(false)
const showEmailForm = ref(false)

const emailForm = ref({
  status: 'discarded',
  subject: '',
  sender: '',
  content: ''
})

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

// Propiedad computada para detectar si el estado está cerrado
const isJobClosed = computed(() => {
  if (!job.value || !job.value.status) return false
  const closedStatuses = ['rejected', 'ghosted', 'discarded', 'hired']
  return closedStatuses.includes(job.value.status.toLowerCase())
})

const fetchJobDetail = async () => {
  loading.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}`)
    if (response.ok) {
      job.value = await response.json()
      emailForm.value.status = job.value.status
      
      // Si la oferta se carga y está cerrada, asegurarnos de cerrar el formulario
      if (isJobClosed.value) {
        showEmailForm.value = false
      }
    }
  } catch (error) {
    console.error('Error al cargar el detalle de la oferta:', error)
  } finally {
    loading.value = false
  }
}

const toggleEmailForm = () => {
  showEmailForm.value = !showEmailForm.value
}

const submitEmailForm = async () => {
  submitting.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}/register-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(emailForm.value)
    })

    if (response.ok) {
      showEmailForm.value = false
      await fetchJobDetail() // Recarga los datos y evaluará automáticamente si el botón debe ocultarse con el nuevo estado
    } else {
      console.error('Error al registrar el correo')
    }
  } catch (error) {
    console.error('Error de red:', error)
  } finally {
    submitting.value = false
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