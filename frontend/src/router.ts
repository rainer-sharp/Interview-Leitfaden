import { createRouter, createWebHistory } from 'vue-router'
import { setUnauthorizedHandler } from './api'
import { checkSession, loggedIn } from './stores/session'
import CatalogEditorView from './views/CatalogEditorView.vue'
import GroupsView from './views/GroupsView.vue'
import GroupView from './views/GroupView.vue'
import ImportView from './views/ImportView.vue'
import LoginView from './views/LoginView.vue'
import InterviewStartView from './views/InterviewStartView.vue'
import InterviewsView from './views/InterviewsView.vue'
import InterviewView from './views/InterviewView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true, focus: true } },
    { path: '/', component: GroupsView },
    { path: '/gruppen/:id', component: GroupView, props: (r) => ({ id: Number(r.params.id) }) },
    { path: '/kataloge/:id', component: CatalogEditorView, props: (r) => ({ id: Number(r.params.id) }) },
    { path: '/gruppen/:id/import', component: ImportView, props: (r) => ({ id: Number(r.params.id) }) },
    { path: '/interviews', component: InterviewsView },
    { path: '/interviews/neu', component: InterviewStartView },
    {
      path: '/interviews/:id',
      component: InterviewView,
      props: (r) => ({ id: Number(r.params.id) }),
      meta: { focus: true },
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  if (await checkSession()) return true
  return { path: '/login', query: { weiter: to.fullPath } }
})

setUnauthorizedHandler(() => {
  loggedIn.value = false
  const current = router.currentRoute.value
  if (!current.meta.public) router.replace({ path: '/login', query: { weiter: current.fullPath } })
})
