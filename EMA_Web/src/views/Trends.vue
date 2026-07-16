<template>
  <div class="page-trends">
    <el-card shadow="never" class="page-card intro-card">
      <h2 class="section-title">心理健康趋势与风险</h2>
      <p class="section-sub">当前评估 · 未来预测 · 异常预警</p>
    </el-card>

    <el-skeleton v-if="loading" :rows="6" animated />

    <el-empty
      v-else-if="!hasAssessment"
      description="完成基线测评或 EMA 打卡后，将展示风险评估与预测信息"
    />

    <template v-else>
      <el-card shadow="never" class="page-card">
        <template #header>
          <div class="card-header">
            <el-tag type="info" effect="plain">01</el-tag>
            <span>当前风险评估</span>
          </div>
        </template>
        <div class="risk-row">
          <el-tag :type="levelTagType" size="large" effect="dark">{{ riskLabel }}</el-tag>
          <span v-if="riskScore != null" class="risk-score">风险指数 {{ riskScore }}</span>
        </div>
        <p class="risk-summary">{{ riskSummary || '暂无摘要' }}</p>
      </el-card>

      <el-card v-if="factors.length" shadow="never" class="page-card">
        <template #header>
          <span>主要影响因素</span>
        </template>
        <el-table :data="factors" stripe style="width: 100%">
          <el-table-column prop="label" label="指标" min-width="120" />
          <el-table-column prop="value" label="数值" min-width="80" />
          <el-table-column prop="source" label="来源" min-width="100" />
        </el-table>
      </el-card>
    </template>

    <el-alert v-if="error" type="error" :title="error" show-icon class="page-alert" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ensureLogin } from '../api/auth'
import { fetchRiskAssessment } from '../api/chat'

const loading = ref(true)
const error = ref('')
const risk = ref(null)

const hasAssessment = computed(() => Boolean(risk.value?.current))
const riskLabel = computed(() => risk.value?.current?.label || risk.value?.current?.level || '未知')
const riskLevel = computed(() => risk.value?.current?.level || '')
const riskScore = computed(() => risk.value?.current?.score)
const riskSummary = computed(() => risk.value?.current?.summary || '')
const factors = computed(() => risk.value?.current?.factors || [])

const levelTagType = computed(() => {
  const level = String(riskLevel.value).toLowerCase()
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'success'
  return 'info'
})

onMounted(async () => {
  loading.value = true
  try {
    await ensureLogin()
    risk.value = await fetchRiskAssessment()
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-card {
  margin-bottom: 16px;
  border-radius: 16px;
}

.intro-card .section-title {
  margin: 0 0 8px;
  font-size: 20px;
  color: #0f6e5c;
}

.section-sub {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.risk-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.risk-score {
  color: #606266;
  font-size: 14px;
}

.risk-summary {
  margin: 0;
  line-height: 1.65;
  color: #303133;
}

.page-alert {
  margin-top: 12px;
}
</style>
