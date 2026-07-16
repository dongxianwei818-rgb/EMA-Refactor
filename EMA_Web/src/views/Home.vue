<template>
  <div>
    <section class="card">
      <h1 class="hero-title">EMA Chat</h1>
      <p class="hint">非诊断支持对话 · 查看反馈与校园资源（由原微信小程序能力重构为 Vue3 Web）</p>
    </section>

    <section class="card">
      <h3 style="margin:0 0 12px">今日反馈摘要</h3>
      <p v-if="loading" class="muted">加载中…</p>
      <template v-else>
        <div class="level" :class="feedback.level || 'unknown'">
          关注等级：{{ feedback.level || 'unknown' }}
        </div>
        <p style="line-height:1.65;margin:0">{{ feedback.message || '暂无反馈' }}</p>
        <p class="disclaimer">{{ feedback.disclaimer }}</p>
      </template>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="btn-row">
        <button class="btn" @click="$router.push('/chat')">进入对话</button>
        <button class="btn secondary" :disabled="loggingIn" @click="relogin">
          {{ loggingIn ? '登录中…' : '重新登录' }}
        </button>
      </div>
      <p class="muted" style="margin-top:12px;font-size:13px">
        openid：{{ openid || '未登录' }}
        <span v-if="userId"> · user_id：{{ userId }}</span>
      </p>
    </section>

    <section class="card" v-if="riskLabel">
      <h3 style="margin:0 0 8px">风险评估（只读）</h3>
      <div class="level" :class="riskLevel">{{ riskLabel }}</div>
      <p class="muted" style="margin:0">{{ riskSummary }}</p>
    </section>

    <!-- 对齐小程序「我的」：查看知情同意 / 撤回授权 -->
    <section class="card">
      <h3 style="margin:0 0 12px">知情同意</h3>
      <div class="btn-row">
        <button
          class="btn secondary"
          @click="$router.push({ path: '/consent', query: { mode: 'view' } })"
        >
          查看知情同意
        </button>
        <button
          v-if="consented"
          class="btn revoke"
          :disabled="revoking"
          @click="onRevokeConsent"
        >
          {{ revoking ? '处理中…' : '撤回授权' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearAuth, ensureLogin, getOpenId, getUserId, loginWithCode } from '../api/auth'
import { fetchFeedback, fetchRiskAssessment } from '../api/chat'
import { recordRevokeLog } from '../api/consent'
import { applyConsentFromServer, hasConsent } from '../utils/consentState'

const router = useRouter()
const feedback = ref({})
const loading = ref(true)
const loggingIn = ref(false)
const revoking = ref(false)
const error = ref('')
const openid = ref('')
const userId = ref('')
const riskLevel = ref('')
const riskLabel = ref('')
const riskSummary = ref('')
const consented = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    await ensureLogin()
    openid.value = getOpenId()
    userId.value = getUserId()
    consented.value = hasConsent()
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

async function relogin() {
  loggingIn.value = true
  error.value = ''
  try {
    clearAuth()
    await loginWithCode()
    await load()
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loggingIn.value = false
  }
}

async function onRevokeConsent() {
  if (!consented.value || revoking.value) return
  const ok = window.confirm(
    '确认撤回知情同意与隐私授权？撤回后将停止新的数据采集，再次使用需重新同意。',
  )
  if (!ok) return
  const at = Date.now()
  revoking.value = true
  try {
    const data = await recordRevokeLog({ source: 'my', page: 'my' }, at)
    applyConsentFromServer({
      has_consent: false,
      status: 'revoke',
      at: data.at || at,
    })
  } catch (e) {
    console.warn('记录撤回授权失败', e)
    applyConsentFromServer({ has_consent: false, status: 'revoke', at })
  } finally {
    consented.value = false
    revoking.value = false
    router.replace('/consent')
  }
}

onMounted(load)
</script>
