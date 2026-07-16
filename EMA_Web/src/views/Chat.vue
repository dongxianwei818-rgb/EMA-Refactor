<template>
  <div class="page-chat">
    <el-card shadow="never" class="chat-card" body-class="chat-body">
      <div ref="listEl" class="msg-list">
        <div
          v-for="m in messages"
          :key="m.id + '-' + (m.created_at || '')"
          class="bubble"
          :class="m.role"
        >
          {{ m.content }}
        </div>
        <el-alert v-if="loadError" type="error" :title="loadError" show-icon :closable="false" />
      </div>

      <div class="composer">
        <el-input
          v-model="draft"
          placeholder="描述困扰，或问：风险评估 / 资源"
          :disabled="sending"
          clearable
          @keyup.enter="onSend"
        />
        <el-button type="primary" :loading="sending" :disabled="!draft.trim()" @click="onSend">
          发送
        </el-button>
      </div>
      <div v-if="disclaimer" class="chat-footer">{{ disclaimer }}</div>
    </el-card>
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

<style scoped>
.chat-card {
  border-radius: 16px;
  overflow: hidden;
}

.chat-card :deep(.chat-body) {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  min-height: 420px;
  padding: 0;
}

.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #e8efec;
}

.bubble {
  max-width: min(78%, 560px);
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 15px;
}

.bubble.user {
  margin-left: auto;
  background: #0f6e5c;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble.assistant,
.bubble.system {
  margin-right: auto;
  background: #fff;
  border-bottom-left-radius: 4px;
}

.composer {
  display: flex;
  gap: 10px;
  padding: 12px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.chat-footer {
  font-size: 11px;
  color: #8a94a0;
  padding: 0 12px 12px;
  background: #fff;
}
</style>
