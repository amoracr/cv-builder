import { createRouter, createWebHistory } from 'vue-router'
import JobIndex from '../views/JobIndex.vue'
import JobDetail from '../views/JobDetail.vue'
import JobCreateView from '../views/AddJob.vue'

const routes = [
  {
    path: '/',
    name: 'JobIndex',
    component: JobIndex
  },
  {
    path: '/jobs/add',
    name: 'JobCreate',
    component: JobCreateView
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