<template>
  <teleport to="body">
    <button
      v-if="visible"
      type="button"
      class="digital-fab"
      :class="{ 'is-dragging': dragging }"
      :style="fabStyle"
      aria-label="打开对话"
      @pointerdown="onPointerDown"
      @click="onClick"
    >
      <img
        class="digital-fab-img"
        :src="digitalPersonSrc"
        alt="数字人助手"
        draggable="false"
      />
    </button>

    <el-drawer
      v-model="open"
      title="对话助手"
      direction="rtl"
      size="min(420px, 100%)"
      append-to-body
      class="digital-chat-drawer"
      body-class="digital-chat-drawer-body"
    >
      <ChatPanel embedded :active="open" />
    </el-drawer>
  </teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getToken } from '../api/auth'
import digitalPersonSrc from '../assets/digitalPerson.png'
import ChatPanel from './ChatPanel.vue'

const POS_KEY = 'ema_digital_fab_top'
const DRAG_THRESHOLD = 6

const route = useRoute()
const open = ref(false)
const topPx = ref(null)
const dragging = ref(false)
const moved = ref(false)

let startY = 0
let startTop = 0
let pointerId = null
let fabSize = 72

const visible = computed(() => {
  void route.fullPath
  if (!getToken()) return false
  if (route.name === 'login') return false
  if (open.value) return false
  return true
})

const fabStyle = computed(() => {
  if (topPx.value == null) {
    return { top: '50%', transform: 'translateY(-50%)' }
  }
  return { top: `${topPx.value}px`, transform: 'none' }
})

function clampTop(y) {
  const margin = 8
  const max = Math.max(margin, window.innerHeight - fabSize - margin)
  return Math.min(max, Math.max(margin, y))
}

function readFabSize() {
  fabSize = window.innerWidth <= 720 ? 60 : 72
}

function loadPosition() {
  readFabSize()
  try {
    const raw = localStorage.getItem(POS_KEY)
    if (raw == null || raw === '') return
    const n = Number(raw)
    if (!Number.isNaN(n)) topPx.value = clampTop(n)
  } catch {
    /* ignore */
  }
}

function savePosition() {
  if (topPx.value == null) return
  try {
    localStorage.setItem(POS_KEY, String(Math.round(topPx.value)))
  } catch {
    /* ignore */
  }
}

function onPointerDown(e) {
  if (e.button != null && e.button !== 0) return
  readFabSize()
  const el = e.currentTarget
  const rect = el.getBoundingClientRect()
  startTop = rect.top
  startY = e.clientY
  topPx.value = startTop
  moved.value = false
  dragging.value = true
  pointerId = e.pointerId
  el.setPointerCapture?.(e.pointerId)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
}

function onPointerMove(e) {
  if (!dragging.value) return
  if (pointerId != null && e.pointerId !== pointerId) return
  const dy = e.clientY - startY
  if (Math.abs(dy) > DRAG_THRESHOLD) moved.value = true
  topPx.value = clampTop(startTop + dy)
}

function onPointerUp(e) {
  if (pointerId != null && e.pointerId !== pointerId) return
  dragging.value = false
  pointerId = null
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  if (moved.value) savePosition()
}

function onClick(e) {
  // 拖动后不打开抽屉
  if (moved.value) {
    e.preventDefault()
    e.stopPropagation()
    moved.value = false
    return
  }
  open.value = true
}

function onResize() {
  readFabSize()
  if (topPx.value != null) topPx.value = clampTop(topPx.value)
}

onMounted(() => {
  loadPosition()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
})

watch(
  () => route.fullPath,
  () => {
    if (route.name === 'login' || !getToken()) open.value = false
  },
)
</script>

<style scoped>
.digital-fab {
  position: fixed;
  right: 20px;
  z-index: 3000;
  width: 72px;
  height: 72px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  cursor: grab;
  touch-action: none;
  user-select: none;
  box-shadow: 0 6px 20px rgba(16, 36, 31, 0.18);
  transition: box-shadow 0.2s ease;
}

.digital-fab:hover:not(.is-dragging) {
  box-shadow: 0 8px 24px rgba(16, 36, 31, 0.24);
}

.digital-fab.is-dragging {
  cursor: grabbing;
  box-shadow: 0 10px 28px rgba(16, 36, 31, 0.28);
}

.digital-fab-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 50%;
  pointer-events: none;
  user-select: none;
}

@media (max-width: 720px) {
  .digital-fab {
    right: 12px;
    width: 60px;
    height: 60px;
  }
}
</style>

<style>
.digital-chat-drawer .el-drawer__body,
.digital-chat-drawer-body {
  padding: 0 !important;
  height: calc(100% - 55px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.digital-chat-drawer .chat-panel {
  flex: 1;
  min-height: 0;
}
</style>
