<template>
  <div class="chat-layout">
    <div ref="listEl" class="msg-list">
      <div
        v-for="m in messages"
        :key="m.id + '-' + (m.created_at || '')"
        class="bubble"
        :class="m.role"
      >
        {{ m.content }}
      </div>
      <p v-if="loadError" class="error">{{ loadError }}</p>
    </div>

    <div class="composer">
      <input
        v-model="draft"
        type="text"
        placeholder="描述困扰，或问：风险评估 / 资源"
        :disabled="sending"
        @keyup.enter="onSend"
      />
      <button class="btn" :disabled="sending || !draft.trim()" @click="onSend">
        {{ sending ? '发送中' : '发送' }}
      </button>
    </div>
    <div class="chat-footer">{{ disclaimer }}</div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { ensureLogin } from '../api/auth'
import { fetchMessages, sendMessage } from '../api/chat'

const messages = ref([])
const draft = ref('')
const sending = ref(false)
const disclaimer = ref('')
const loadError = ref('')
const listEl = ref(null)

function scrollBottom() {
  nextTick(() => {
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
}

async function loadMessages() {
  loadError.value = ''
  try {
    await ensureLogin()
    const data = await fetchMessages(80)
    messages.value = data?.items || []
    disclaimer.value = data?.disclaimer || ''
    scrollBottom()
  } catch (e) {
    loadError.value = e.message || String(e)
  }
}

async function onSend() {
  const text = draft.value.trim()
  if (!text || sending.value) return
  sending.value = true
  try {
    const data = await sendMessage(text)
    const next = messages.value.slice()
    if (data.user_message) next.push(data.user_message)
    if (data.assistant_message) next.push(data.assistant_message)
    messages.value = next
    draft.value = ''
    if (data.disclaimer) disclaimer.value = data.disclaimer
    scrollBottom()
  } catch (e) {
    loadError.value = e.message || String(e)
  } finally {
    sending.value = false
  }
}

onMounted(loadMessages)
</script>
