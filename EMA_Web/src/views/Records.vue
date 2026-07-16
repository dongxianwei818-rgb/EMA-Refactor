<template>
  <div class="page-records">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>采集记录</span>
          <el-tag v-if="sessions.length" type="success" effect="plain">
            {{ sessions.length }} 次打卡
          </el-tag>
        </div>
      </template>

      <el-skeleton v-if="loading" :rows="4" animated />
      <el-alert v-else-if="error" type="error" :title="error" show-icon :closable="false" />

      <el-empty v-else-if="!sessions.length" description="暂无采集记录">
        <template #description>
          <p>完成 EMA 打卡后，问卷、日记、语音等采集项将在此按会话展示。</p>
        </template>
      </el-empty>

      <el-collapse v-else accordion>
        <el-collapse-item
          v-for="session in sessions"
          :key="session.key"
          :name="session.key"
        >
          <template #title>
            <div class="session-title">
              <el-tag size="small" type="primary" effect="plain">
                第 {{ session.sessionId }} 次打卡
              </el-tag>
              <span>{{ session.dateLabel }}</span>
              <span class="session-meta">{{ session.itemCount }} 项 · {{ session.timeRange }}</span>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="record in session.items"
              :key="record.id"
              :timestamp="record.timeLabel"
              placement="top"
            >
              <el-tag size="small" effect="light">{{ record.typeLabel }}</el-tag>
              <p class="record-summary">{{ record.summary }}</p>
            </el-timeline-item>
          </el-timeline>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ensureLogin } from '../api/auth'

const loading = ref(true)
const error = ref('')
const sessions = ref([])

onMounted(async () => {
  loading.value = true
  try {
    await ensureLogin()
    // Web 端记录列表 API 待对接；先展示空状态
    sessions.value = []
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-card {
  border-radius: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.session-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.session-meta {
  color: #909399;
  font-size: 12px;
}

.record-summary {
  margin: 8px 0 0;
  line-height: 1.6;
  color: #606266;
}
</style>
