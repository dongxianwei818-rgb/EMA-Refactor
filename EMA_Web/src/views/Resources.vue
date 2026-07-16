<template>
  <div>
    <section class="card">
      <h1 class="hero-title" style="font-size:24px">心理健康资源</h1>
      <p class="hint">紧急情况请优先拨打热线或前往校内心理中心。</p>
    </section>

    <p v-if="loading" class="muted">加载中…</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="card resource-item" v-for="(item, idx) in resources" :key="idx">
      <div class="name">{{ item.title }}</div>
      <div class="muted">{{ item.desc }}</div>
      <a
        v-if="item.phone"
        class="phone"
        :href="'tel:' + item.phone"
      >电话：{{ item.phone }}</a>
    </section>
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
