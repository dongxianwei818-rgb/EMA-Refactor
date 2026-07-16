<template>
  <div class="page-resources">
    <el-card shadow="never" class="page-card">
      <h1 class="hero-title">心理健康资源</h1>
      <p class="hint">紧急情况请优先拨打热线或前往校内心理中心。</p>
    </el-card>

    <el-skeleton v-if="loading" :rows="4" animated />
    <el-alert v-else-if="error" type="error" :title="error" show-icon :closable="false" />

    <el-empty v-else-if="!resources.length" description="暂无资源" />

    <el-card
      v-for="(item, idx) in resources"
      :key="idx"
      shadow="never"
      class="page-card resource-item"
    >
      <div class="name">{{ item.title }}</div>
      <p class="muted">{{ item.desc }}</p>
      <el-link v-if="item.phone" type="primary" :href="'tel:' + item.phone">
        电话：{{ item.phone }}
      </el-link>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ensureLogin } from '../api/auth'
import { fetchResources } from '../api/chat'

const resources = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  loading.value = true
  try {
    await ensureLogin()
    resources.value = (await fetchResources()) || []
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

.hero-title {
  margin: 0 0 8px;
  font-size: 22px;
  color: #0f6e5c;
}

.hint,
.muted {
  color: #909399;
  line-height: 1.6;
  margin: 0;
}

.name {
  font-weight: 600;
  margin-bottom: 8px;
}

.resource-item .muted {
  margin-bottom: 8px;
}
</style>
