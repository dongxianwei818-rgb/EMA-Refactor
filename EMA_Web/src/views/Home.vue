<template>
  <div class="page-home">
    <el-card shadow="never" class="page-card hero-card">
      <h1 class="hero-title">EMA</h1>
      <p class="hint">非诊断支持 · 生态瞬时评估与心理健康资源</p>
    </el-card>

    <el-card shadow="never" class="page-card">
      <template #header>
        <span>今日反馈摘要</span>
      </template>
      <el-skeleton v-if="loading" :rows="3" animated />
      <template v-else>
        <el-tag :type="levelTagType" effect="dark" class="level-tag">
          关注等级：{{ feedback.level || 'unknown' }}
        </el-tag>
        <p class="feedback-msg">{{ feedback.message || '暂无反馈' }}</p>
        <p class="disclaimer">{{ feedback.disclaimer }}</p>
      </template>
      <el-alert v-if="error" type="error" :title="error" show-icon class="page-alert" />
      <div class="btn-row">
        <el-button type="primary" @click="$router.push('/chat')">进入对话</el-button>
        <el-button @click="$router.push('/trends')">查看趋势</el-button>
      </div>
    </el-card>

    <el-card v-if="riskLabel" shadow="never" class="page-card">
      <template #header>
        <span>风险评估（只读）</span>
      </template>
      <el-tag :type="riskTagType" effect="plain">{{ riskLabel }}</el-tag>
      <p class="muted">{{ riskSummary }}</p>
    </el-card>

    <el-row :gutter="12" class="quick-nav">
      <el-col :span="8" v-for="item in shortcuts" :key="item.path">
        <el-card shadow="hover" class="shortcut-card" @click="$router.push(item.path)">
          <el-icon :size="22" color="#0f6e5c">
            <component :is="item.icon" />
          </el-icon>
          <div class="shortcut-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChatDotRound, Collection, Document } from '@element-plus/icons-vue'
import { ensureLogin } from '../api/auth'
import { fetchFeedback, fetchRiskAssessment } from '../api/chat'

const feedback = ref({})
const loading = ref(true)
const error = ref('')
const riskLevel = ref('')
const riskLabel = ref('')
const riskSummary = ref('')

const shortcuts = [
  { path: '/records', label: '记录', icon: Document },
  { path: '/chat', label: '对话', icon: ChatDotRound },
  { path: '/resources', label: '资源', icon: Collection },
]

const levelTagType = computed(() => {
  const level = String(feedback.value.level || '').toLowerCase()
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'success'
  return 'info'
})

const riskTagType = computed(() => {
  const level = String(riskLevel.value).toLowerCase()
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'success'
  return 'info'
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    await ensureLogin()
    feedback.value = (await fetchFeedback()) || {}
    try {
      const risk = await fetchRiskAssessment()
      riskLevel.value = risk?.current?.level || ''
      riskLabel.value = risk?.current?.label || riskLevel.value
      riskSummary.value = risk?.current?.summary || ''
    } catch {
      /* 风险接口失败不影响主流程 */
    }
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-card {
  margin-bottom: 16px;
  border-radius: 16px;
}

.hero-title {
  margin: 0 0 8px;
  font-size: 28px;
  color: #0f6e5c;
}

.hint,
.muted {
  color: #909399;
  line-height: 1.6;
  margin: 0;
}

.level-tag {
  margin-bottom: 10px;
}

.feedback-msg {
  line-height: 1.65;
  margin: 0;
}

.disclaimer {
  font-size: 12px;
  color: #8a94a0;
  line-height: 1.5;
  margin-top: 12px;
}

.btn-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.page-alert {
  margin-top: 12px;
}

.quick-nav {
  margin-top: 4px;
}

.shortcut-card {
  text-align: center;
  cursor: pointer;
  border-radius: 12px;
  margin-bottom: 12px;
}

.shortcut-label {
  margin-top: 8px;
  font-size: 13px;
  color: #303133;
}
</style>
