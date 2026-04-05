import { createRouter, createWebHistory } from 'vue-router'

import Detect from '../pages/Detect.vue'
import History from '../pages/History.vue'
import Detail from '../pages/Detail.vue'
import Recommend from '../pages/Recommend.vue'
import Assist from '../pages/Assist.vue'
import About from '../pages/About.vue'

const routes = [
  { path: '/', redirect: '/detect' },
  { path: '/detect', component: Detect },
  { path: '/history', component: History },
  { path: '/history/:id', component: Detail },
  { path: '/recommend', component: Recommend },
  { path: '/assist', component: Assist },
  { path: '/about', component: About },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router