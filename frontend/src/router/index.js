import { createRouter, createWebHistory } from 'vue-router'
import JobIndex from '../views/JobIndex.vue' // O tu App.vue adaptado como vista principal
import JobDetail from '../views/JobDetail.vue'

const routes = [
  {
    path: '/',
    name: 'JobIndex',
    component: JobIndex
  },
  {
    path: '/jobs/:id',
    name: 'JobDetail',
    component: JobDetail,
    props: route => ({ jobId: Number(route.params.id) })
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router