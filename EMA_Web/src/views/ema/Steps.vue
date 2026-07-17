<template>
  <div class="ema-task-page">
    <el-card shadow="never">
      <h2>运动步数</h2>
      <p class="hint">Web 端请手动输入今日步数（小程序端可同步微信运动）</p>

      <el-form label-position="top">
        <el-form-item label="今日步数">
          <el-input-number v-model="stepCount" :min="0" :max="99999" :step="100" style="width: 100%" />
        </el-form-item>
      </el-form>

      <el-descriptions v-if="analytics.baseline" :column="2" border size="small" class="analytics">
        <el-descriptions-item label="7日均值">{{ analytics.avg7 }}</el-descriptions-item>
        <el-descriptions-item label="个体基线">{{ analytics.baseline }}</el-descriptions-item>
        <el-descriptions-item label="偏差">{{ analytics.deviation }}%</el-descriptions-item>
        <el-descriptions-item label="低活动连续天">{{ analytics.lowDays }}</el-descriptions-item>
      </el-descriptions>

      <el-button type="primary" class="submit-btn" :loading="submitting" @click="onSubmit">
        完成今日打卡
      </el-button>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { saveRiskSnapshot, submitStepLog } from '../../api/ema'
import {
  ensureCheckinSession,
  getCurrentSessionId,
  getStepsAnalytics,
  getTodayKey,
  markTaskDone,
  saveStepsHistory,
  saveSubmission,
} from '../../utils/ema'
import { goHome, runStepSubmit } from '../../utils/emaFlow'
import { endTaskTimer, startTaskTimer, trackEvent } from '../../utils/tracker'

const router = useRouter()
const stepCount = ref(5000)
const submitting = ref(false)
const analytics = ref({})

onMounted(() => {
  ensureCheckinSession()
  analytics.value = getStepsAnalytics()
  if (analytics.value.today) stepCount.value = analytics.value.today
  trackEvent('steps', 'view', {}, '/ema/steps')
  startTaskTimer('steps')
})

async function onSubmit() {
  if (submitting.value) return
  const n = Number(stepCount.value)
  if (!n || n < 0) {
    ElMessage.warning('请填写步数')
    return
  }
  submitting.value = true
  const at = Date.now()
  saveStepsHistory(n)
  markTaskDone('steps')
  saveSubmission('steps', { steps: n, source: 'manual', analytics: getStepsAnalytics() })
  endTaskTimer('steps')
  trackEvent('steps', 'submit', { steps: n })
  try {
    await runStepSubmit({
      router,
      goNext: false,
      submit: async () => {
        await submitStepLog(n, 'manual', at, getCurrentSessionId(), getTodayKey(), getStepsAnalytics())
        await saveRiskSnapshot(getTodayKey(), getCurrentSessionId(), at)
      },
      successToast: '今日打卡完成',
      onSuccess: () => goHome(router, 400),
    })
  } catch (e) {
    ElMessage.error(e.message || '提交失败')
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

.hint {
  color: #909399;
  margin-bottom: 20px;
}

.analytics {
  margin: 16px 0;
}

.submit-btn {
  width: 100%;
  margin-top: 12px;
}
</style>
