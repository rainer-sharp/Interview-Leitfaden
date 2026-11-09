import { createRouter, createWebHistory } from 'vue-router'
import CatalogEditorView from './views/CatalogEditorView.vue'
import GroupsView from './views/GroupsView.vue'
import GroupView from './views/GroupView.vue'
import ImportView from './views/ImportView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: GroupsView },
    { path: '/gruppen/:id', component: GroupView, props: (r) => ({ id: Number(r.params.id) }) },
    { path: '/kataloge/:id', component: CatalogEditorView, props: (r) => ({ id: Number(r.params.id) }) },
    { path: '/gruppen/:id/import', component: ImportView, props: (r) => ({ id: Number(r.params.id) }) },
  ],
})
