<template>
  <div class="ema-task-page">
    <el-card shadow="never">
      <h2>文本日记</h2>
      <p class="prompt">{{ prompt }}</p>
      <el-input
        v-model="text"
        type="textarea"
        :rows="6"
        :maxlength="maxLen"
        show-word-limit
        placeholder="请用 30–100 字描述今天的状态"
        @input="onInput"
      />
      <p class="len-hint" :class="{ valid }">{{ len }} / {{ minLen }}–{{ maxLen }} 字</p>
      <el-button type="primary" class="submit-btn" :loading="submitting" :disabled="!valid" @click="onSubmit">
        提交日记
      </el-button>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { DIARY_MAX, DIARY_MIN, DIARY_PROMPTS } from '../../constants/ema'
import { submitDiaryLog } from '../../api/ema'
import {
  ensureCheckinSession,
  getCurrentSessionId,
  getTodayKey,
  markTaskDone,
  saveSubmission,
} from '../../utils/ema'
import { runStepSubmit } from '../../utils/emaFlow'
import { endTaskTimer, startTaskTimer, trackEvent } from '../../utils/tracker'

const router = useRouter()
const prompt = DIARY_PROMPTS.join('\n')
const text = ref('')
const len = ref(0)
const minLen = DIARY_MIN
const maxLen = DIARY_MAX
const submitting = ref(false)
const valid = computed(() => len.value >= minLen && len.value <= maxLen)

onMounted(() => {
  ensureCheckinSession()
  trackEvent('diary', 'view', {}, '/ema/diary')
  startTaskTimer('diary')
})

function onInput(val) {
  const s = typeof val === 'string' ? val : text.value
  len.value = s.length
}

async function onSubmit() {
  if (!valid.value || submitting.value) return
  submitting.value = true
  const at = Date.now()
  markTaskDone('diary')
  saveSubmission('diary', { text: text.value, prompt })
  endTaskTimer('diary')
  trackEvent('diary', 'submit', { length: len.value })
  try {
    await runStepSubmit({
      router,
      submit: () =>
        submitDiaryLog(text.value, len.value, at, getCurrentSessionId(), getTodayKey()),
      successToast: '已提交',
    })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.ema-task-page {
  max-width: 640px;
  margin: 0 auto;
}

.prompt {
  white-space: pre-line;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 16px;
}

.len-hint {
  text-align: right;
  color: #909399;
  font-size: 13px;
}

.len-hint.valid {
  color: #67c23a;
}

.submit-btn {
  width: 100%;
  margin-top: 16px;
}
</style>
