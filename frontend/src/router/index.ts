import { createRouter, createWebHashHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: ChatView,
    },
    {
      path: '/c/:sessionId',
      name: 'chat',
      component: ChatView,
      props: true,
    },
    {
      path: '/test-segments',
      name: 'test-segments',
      component: () => import('@/views/TestSegments.vue'),
    },
  ],
})

export default router
