<template>
    <div class="job-create-container">
        <div class="header-section">
            <button class="btn-back" @click="router.back()">← Volver</button>
            <h1>Añadir Nueva Oferta de Empleo (Manual)</h1>
        </div>

        <form @submit.prevent="handleSubmit" class="job-form">
            <!-- Título -->
            <div class="form-group">
                <label for="title">Título de la Oferta *</label>
                <input id="title" v-model="form.title" type="text" placeholder="ej. Senior Backend Engineer" required />
            </div>

            <!-- URL -->
            <div class="form-group">
                <label for="url">URL de la Oferta *</label>
                <input id="url" v-model="form.url" type="url" placeholder="https://..." required />
            </div>

            <!-- Sector y Nombre de Empresa -->
            <div class="form-row">
                <div class="form-group">
                    <label for="sector">Sector *</label>
                    <select id="sector" v-model="form.sector" required>
                        <option value="private">Private</option>
                        <option value="public">Public</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="company_name">Empresa *</label>
                    <input id="company_name" v-model="form.company_name" type="text" required />
                </div>
            </div>

            <!-- Nombre de la Fuente (Cargado dinámicamente desde /sources/) -->
            <div class="form-group">
                <label for="source_name">Fuente (Source Name) *</label>
                <select id="source_name" v-model="form.source_name" required>
                    <option value="" disabled>Seleccione una fuente</option>
                    <option v-for="(source, index) in sources" :key="index" :value="source.name || source">
                        {{ source.name || source }}
                    </option>
                </select>
            </div>

            <!-- Descripción -->
            <div class="form-group">
                <label for="description">Descripción de la Vacante *</label>
                <textarea id="description" v-model="form.description" rows="8" placeholder="Detalles sobre el puesto..."
                    required></textarea>
            </div>

            <!-- Acciones -->
            <div class="form-actions">
                <button type="button" class="btn-secondary" @click="router.back()" :disabled="loading">
                    Cancelar
                </button>
                <button type="submit" class="btn-primary" :disabled="loading">
                    <span v-if="loading">Guardando...</span>
                    <span v-else>Guardar Oferta</span>
                </button>
            </div>
        </form>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const router = useRouter()
const loading = ref(false)
const sources = ref([])

const form = reactive({
    title: '',
    url: '',
    description: '',
    sector: 'private',
    company_name: 'Manual',
    source_name: ''
})

// Cargar las fuentes desde el endpoint GET /sources/
const fetchSources = async () => {
    try {
        let url = `${API_URL}/sources/`
        const response = await fetch(url)
        if (response.ok) {
            sources.value = await response.json()
            if (sources.value.length > 0) {
                // Asigna el primer valor por defecto adaptándose a si es array de objetos o strings
                form.source_name = sources.value[0].name || sources.value[0]
            }
        }
    } catch (error) {
        console.error('Error al cargar las fuentes:', error)
    }
}

const handleSubmit = async () => {
    loading.value = true

    try {
        let url = `${API_URL}/jobs/`
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(form)
        })

        if (response.ok) {
            router.push('/')
        } else {
            const errData = await response.json()
            alert(`Error al guardar: ${errData.detail || 'Verifique los datos'}`)
        }
    } catch (error) {
        console.error('Error en la petición POST:', error)
        alert('Error de conexión al guardar la oferta.')
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    fetchSources()
})
</script>

