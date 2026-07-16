<template>
  <div class="page-my">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>账号信息</span>
          <el-button link type="primary" :loading="loggingOut" @click="logout">
            退出登录
          </el-button>
        </div>
      </template>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="用户名">
          {{ profile.user_name || userName || '未登录' }}
        </el-descriptions-item>
        <el-descriptions-item v-if="userId" label="用户 ID">
          {{ userId }}
        </el-descriptions-item>
        <el-descriptions-item v-if="roleLabel" label="角色">
          {{ roleLabel }}
        </el-descriptions-item>
        <el-descriptions-item v-if="profile.research_id" label="研究编号">
          {{ profile.research_id }}
        </el-descriptions-item>
        <el-descriptions-item label="研究状态">
          <el-tag size="small" :type="profile.study_status === 'active' ? 'success' : 'info'">
            {{ profile.study_status || '—' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="!isAdminUser" shadow="never" class="page-card">
      <template #header>
        <span>知情同意</span>
      </template>
      <div class="btn-group">
        <el-button @click="goConsentView">查看知情同意</el-button>
        <el-button
          v-if="consented"
          type="danger"
          plain
          :loading="revoking"
          @click="onRevokeConsent"
        >
          撤回授权
        </el-button>
      </div>
    </el-card>

    <el-alert
      title="非诊断支持工具，不能替代专业医疗或心理咨询。"
      type="info"
      :closable="false"
      show-icon
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ensureLogin,
  fetchProfile,
  getRole,
  getUserId,
  getUserName,
  isAdmin,
  logout as logoutSession,
} from '../api/auth'
import { recordRevokeLog } from '../api/consent'
import { applyConsentFromServer, hasConsent } from '../utils/consentState'

const router = useRouter()
const profile = ref({})
const userName = ref('')
const userId = ref('')
const consented = ref(false)
const revoking = ref(false)
const loggingOut = ref(false)
const isAdminUser = ref(false)

const roleLabel = computed(() => {
  const role = profile.value.role ?? getRole()
  if (role === 0) return '管理员'
  if (role === 1 || role == null) return '普通用户'
  return String(role)
})

async function load() {
  await ensureLogin()
  userName.value = getUserName()
  userId.value = getUserId()
  isAdminUser.value = isAdmin()
  consented.value = hasConsent()
  try {
    profile.value = (await fetchProfile()) || {}
  } catch {
    profile.value = {}
  }
}

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await logoutSession()
  } finally {
    loggingOut.value = false
    router.replace('/login')
  }
}

function goConsentView() {
  router.push({ path: '/consent', query: { mode: 'view' } })
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

<style scoped>
.page-card {
  margin-bottom: 16px;
  border-radius: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
