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
            <span v-if="job.updated_at">Actualizada: {{ formatDate(job.updated_at) }}</span>
          </div>
        </div>

        <div class="header-actions">
          <a :href="job.url" target="_blank" class="btn-external">Ver oferta original ↗</a>

          <button v-if="job.status === 'to_apply' && !job.tailored_cv" @click="generateCv" class="btn-generate-cv"
            :disabled="generatingCv">
            {{ generatingCv ? 'Generando documentos...' : '📄 Generar Documentos ATS' }}
          </button>

          <button v-if="!isJobClosed" @click="toggleForm('status')" class="btn-toggle-status">
            {{ showStatusForm ? 'Cerrar form estado' : '✏️ Cambiar Estado' }}
          </button>

          <button v-if="!isJobClosed" @click="toggleForm('email')" class="btn-register-email">
            <span>{{ showEmailForm ? 'Cerrar form correo' : '✉️ Registrar Correo' }}</span>
          </button>
        </div>
      </header>

      <!-- FORMULARIO 1: Cambiar estado -->
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

      <!-- FORMULARIO 2: Registrar correo -->
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

      <!-- Análisis de IA -->
      <div class="section">
        <h3>Análisis de IA (Match: {{ job.match_percentage }}%)</h3>
        <p class="reasoning">{{ job.ai_reasoning || 'Sin análisis previo.' }}</p>
      </div>

      <!-- PESTAÑAS -->
      <div class="tabs-navigation">
        <button :class="['tab-btn', activeTab === 'description' ? 'active' : '']" @click="activeTab = 'description'">
          📋 Descripción del Puesto
        </button>
        <button v-if="job.tailored_cv?.markdown_content" :class="['tab-btn', activeTab === 'cv' ? 'active' : '']"
          @click="activeTab = 'cv'">
          📄 CV Adaptado (ATS)
        </button>
        <button v-if="job.tailored_cv?.cover_letter" :class="['tab-btn', activeTab === 'coverLetter' ? 'active' : '']"
          @click="activeTab = 'coverLetter'">
          ✉️ Carta de Presentación
        </button>
      </div>

      <!-- CONTENIDO PESTAÑA: Descripción -->
      <div v-if="activeTab === 'description'" class="section tab-content">
        <div class="description-box" v-html="job.description || 'Sin descripción detallada.'"></div>
      </div>

      <!-- CONTENIDO PESTAÑA: CV (Lectura y Edición) -->
      <div v-if="activeTab === 'cv' && job.tailored_cv?.markdown_content" class="section tab-content cv-tab-wrapper">
        <div class="cv-actions-bar">
          <div class="left-actions">
            <button @click="downloadCvPdf" class="btn-download-pdf">
              📥 Descargar CV en PDF
            </button>
          </div>
          <div class="right-actions">
            <template v-if="!isEditingCv">
              <button @click="startEditCv" class="btn-edit-mode">✏️ Editar CV</button>
            </template>
            <template v-else>
              <button @click="cancelEditCv" class="btn-cancel-edit">Cancelar</button>
              <button @click="saveCv" class="btn-save-edit" :disabled="savingCv">
                {{ savingCv ? 'Guardando...' : '💾 Guardar Cambios' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Textarea para editar o Vista previa Markdown -->
        <div v-if="isEditingCv" class="edit-wrapper">
          <textarea v-model="editableCvContent" rows="20" class="form-control markdown-textarea"></textarea>
        </div>
        <div v-else class="markdown-body cv-preview-box" v-html="renderedCvMarkdown"></div>
      </div>

      <!-- CONTENIDO PESTAÑA: Carta de Presentación (Lectura y Edición) -->
      <div v-if="activeTab === 'coverLetter' && job.tailored_cv?.cover_letter"
        class="section tab-content cv-tab-wrapper">
        <div class="cv-actions-bar">
          <div class="left-actions">
            <button @click="downloadCoverLetterPdf" class="btn-download-pdf">
              📥 Descargar Carta en PDF
            </button>
          </div>
          <div class="right-actions">
            <template v-if="!isEditingCl">
              <button @click="startEditCl" class="btn-edit-mode">✏️ Editar Carta</button>
            </template>
            <template v-else>
              <button @click="cancelEditCl" class="btn-cancel-edit">Cancelar</button>
              <button @click="saveCoverLetter" class="btn-save-edit" :disabled="savingCl">
                {{ savingCl ? 'Guardando...' : '💾 Guardar Cambios' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Textarea para editar o Vista previa Markdown -->
        <div v-if="isEditingCl" class="edit-wrapper">
          <textarea v-model="editableClContent" rows="20" class="form-control markdown-textarea"></textarea>
        </div>
        <div v-else class="markdown-body cv-preview-box" v-html="renderedCoverLetterMarkdown"></div>
      </div>

      <!-- Historial de Correos -->
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
import { marked } from 'marked'

const router = useRouter()
const route = useRoute()
const jobId = Number(route.params.id)

const job = ref(null)
const loading = ref(false)
const submittingStatus = ref(false)
const submittingEmail = ref(false)
const generatingCv = ref(false)

// Estados de guardado y edición para CV y Carta
const savingCv = ref(false)
const savingCl = ref(false)
const isEditingCv = ref(false)
const isEditingCl = ref(false)
const editableCvContent = ref('')
const editableClContent = ref('')

const activeTab = ref('description')

const showStatusForm = ref(false)
const showEmailForm = ref(false)

const statusForm = ref({ status: '' })
const emailForm = ref({ subject: '', sender: '', content: '' })

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const isJobClosed = computed(() => {
  if (!job.value || !job.value.status) return false
  const currentStatus = String(job.value.status).trim().toLowerCase()
  return ['rejected', 'ghosted', 'discarded', 'hired'].includes(currentStatus)
})

const renderedCvMarkdown = computed(() => {
  if (!job.value?.tailored_cv?.markdown_content) return ''
  return marked(job.value.tailored_cv.markdown_content)
})

const renderedCoverLetterMarkdown = computed(() => {
  if (!job.value?.tailored_cv?.cover_letter) return ''
  return marked(job.value.tailored_cv.cover_letter)
})

const fetchJobDetail = async () => {
  loading.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}`)
    if (response.ok) {
      job.value = await response.json()
      statusForm.value.status = job.value.status
    }
  } catch (error) {
    console.error('Error al cargar el detalle de la oferta:', error)
  } finally {
    loading.value = false
  }
}

// Métodos de Edición de CV
const startEditCv = () => {
  editableCvContent.value = job.value.tailored_cv?.markdown_content || ''
  isEditingCv.value = true
}

const cancelEditCv = () => {
  isEditingCv.value = false
  editableCvContent.value = ''
}

const saveCv = async () => {
  savingCv.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}/tailored-cv`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown_content: editableCvContent.value })
    })
    if (response.ok) {
      job.value.tailored_cv.markdown_content = editableCvContent.value
      isEditingCv.value = false
    }
  } catch (error) {
    console.error('Error al guardar el CV:', error)
  } finally {
    savingCv.value = false
  }
}

// Métodos de Edición de Carta de Presentación
const startEditCl = () => {
  editableClContent.value = job.value.tailored_cv?.cover_letter || ''
  isEditingCl.value = true
}

const cancelEditCl = () => {
  isEditingCl.value = false
  editableClContent.value = ''
}

const saveCoverLetter = async () => {
  savingCl.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}/tailored-cv`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cover_letter: editableClContent.value })
    })
    if (response.ok) {
      job.value.tailored_cv.cover_letter = editableClContent.value
      isEditingCl.value = false
    }
  } catch (error) {
    console.error('Error al guardar la carta de presentación:', error)
  } finally {
    savingCl.value = false
  }
}

const toggleForm = (formType) => {
  if (formType === 'status') {
    showStatusForm.value = !showStatusForm.value
    if (showStatusForm.value) showEmailForm.value = false
  } else {
    showEmailForm.value = !showEmailForm.value
    if (showEmailForm.value) showStatusForm.value = false
  }
}

const submitStatusForm = async () => {
  submittingStatus.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: statusForm.value.status })
    })
    if (response.ok) {
      showStatusForm.value = false
      await fetchJobDetail()
    }
  } catch (error) {
    console.error('Error de red:', error)
  } finally {
    submittingStatus.value = false
  }
}

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
    }
  } catch (error) {
    console.error('Error de red:', error)
  } finally {
    submittingEmail.value = false
  }
}

const generateCv = async () => {
  generatingCv.value = true
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}/generate-cv`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    if (response.ok) {
      await fetchJobDetail()
      activeTab.value = 'cv'
    }
  } catch (error) {
    console.error('Error al generar los documentos:', error)
  } finally {
    generatingCv.value = false
  }
}

const downloadCvPdf = () => {
  window.open(`${API_URL}/jobs/${jobId}/download-cv-pdf`, '_blank')
}

const downloadCoverLetterPdf = () => {
  window.open(`${API_URL}/jobs/${jobId}/download-cl-pdf`, '_blank')
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