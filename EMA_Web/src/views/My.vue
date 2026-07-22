<template>
  <div class="page-my">
    <div class="profile-container">
      <section class="card profile-card kv-card">
        <div class="profile-card-head">
          <h3 class="section-title">基本信息</h3>
          <button type="button" class="profile-more" @click="goProfileDetail">
            {{ hasBaselineBound ? "查看详情" : "去填写" }}
            <span class="profile-more-arrow">›</span>
          </button>
        </div>

        <template v-if="hasBaselineBound">
          <div class="profile-id">用户名：{{ userName }}</div>
          <div class="kv-list">
            <div
              v-for="(item, idx) in basicInfo"
              :key="item.id || item.label"
              class="profile-row"
              :class="{ 'is-last': idx === basicInfo.length - 1 }"
            >
              <span class="profile-label" :class="`label-${item.id}`">{{
                item.label
              }}</span>
              <span class="profile-value">{{ item.value }}</span>
            </div>
          </div>
          <p v-if="!basicInfo.length && !researchId" class="profile-empty">
            暂无已填写的基本信息
          </p>
        </template>
        <p v-else class="profile-empty">尚未完成基线测评，点击前往填写。</p>
      </section>

      <section class="card profile-card kv-card">
        <div class="profile-card-head">
          <h3 class="section-title">使用行为</h3>
          <button type="button" class="profile-more" @click="goBehaviorDetail">
            查看详情
            <span class="profile-more-arrow">›</span>
          </button>
        </div>
        <div class="kv-list">
          <div
            v-for="(item, idx) in behaviorInfo"
            :key="item.id"
            class="profile-row"
            :class="{ 'is-last': idx === behaviorInfo.length - 1 }"
          >
            <span class="profile-label" :class="`label-${item.id}`">{{
              item.label
            }}</span>
            <span class="profile-value">{{ item.value }} {{ item.unit }}</span>
          </div>
        </div>
        <p class="kv-footnote">连续缺测天数可作研究信号参考</p>
      </section>
    </div>
    <div class="button-container">
      <template v-if="!isAdminUser">
        <button type="button" class="btn-secondary" @click="goConsentView">
          查看知情同意
        </button>
        <button
          v-if="consented"
          type="button"
          class="btn-revoke"
          :disabled="revoking"
          @click="onRevokeConsent"
        >
          {{ revoking ? "处理中…" : "撤回授权" }}
        </button>
        <button
          type="button"
          class="btn-secondary btn-exit"
          :disabled="exiting"
          @click="exitStudy"
        >
          {{ exiting ? "退出中…" : "退出研究" }}
        </button>
      </template>

      <button
        v-else
        type="button"
        class="btn-secondary"
        :disabled="loggingOut"
        @click="logout"
      >
        {{ loggingOut ? "退出中…" : "退出登录" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  clearAuth,
  ensureLogin,
  getUserName,
  isAdmin,
  logout as logoutSession,
} from "../api/auth";
import { recordExitLog, recordRevokeLog } from "../api/consent";
import { getBehaviorStats } from "../utils/behaviorStats";
import {
  applyConsentFromServer,
  getServerProfile,
  hasConsent,
} from "../utils/consentState";
import {
  ensureBaselineProfile,
  hasBaseline,
  isResearchBound,
} from "../utils/ema";
import { hydrateFromServer } from "../utils/hydrate";
import { invalidateOnboardingGate } from "../utils/onboardingGate";
import { buildBasicSummary } from "../utils/profile";
import { trackEvent } from "../utils/tracker";

const router = useRouter();
const profile = ref({});
const basicInfo = ref([]);
const hasBaselineBound = ref(false);
const consented = ref(false);
const stats = ref({});
const revoking = ref(false);
const exiting = ref(false);
const loggingOut = ref(false);
const isAdminUser = ref(false);

const researchId = computed(
  () => profile.value.researchId || profile.value.research_id || "",
);
const userName = computed(
  () =>
    profile.value.userName || profile.value.user_name || getUserName() || "—",
);
const checkinHoursText = computed(() => {
  const hours = stats.value.checkinHours || [];
  return hours.length ? hours.join(", ") : "—";
});
const behaviorInfo = computed(() => {
  const s = stats.value || {};
  return [
    { id: "openCount", label: "打开次数", value: s.openCount ?? 0, unit: "次" },
    {
      id: "missedDays",
      label: "连续缺测天数",
      value: s.missedDays ?? 0,
      unit: "天",
    },
    {
      id: "avgDiary",
      label: "平均日记字数",
      value: s.avgDiaryWords ?? 0,
      unit: "字",
    },
    {
      id: "avgVoice",
      label: "平均语音时长",
      value: `${s.avgVoiceSec ?? 0}`,
      unit: "秒",
    },
    {
      id: "avgVideo",
      label: "平均视频时长",
      value: `${s.avgVideoSec ?? 0}`,
      unit: "秒",
    },
    {
      id: "voiceSkips",
      label: "语音跳过次数",
      value: s.voiceSkips ?? 0,
      unit: "次",
    },
    {
      id: "videoSkips",
      label: "视频跳过次数",
      value: s.videoSkips ?? 0,
      unit: "次",
    },
    {
      id: "checkinHours",
      label: "最近打卡时段(时)",
      value: checkinHoursText.value,
      unit: "时",
    },
  ];
});

function applyProfile(local) {
  const server = getServerProfile() || {};
  const p = {
    ...local,
    researchId:
      local.researchId || local.research_id || server.research_id || "",
    userName:
      local.userName ||
      local.user_name ||
      server.user_name ||
      getUserName() ||
      "",
  };
  profile.value = p;
  basicInfo.value = buildBasicSummary(p);
  hasBaselineBound.value = isResearchBound() || hasBaseline();
  consented.value = hasConsent();
  isAdminUser.value = isAdmin();
  stats.value = getBehaviorStats();
}

async function refresh() {
  try {
    await hydrateFromServer();
  } catch (e) {
    console.warn("同步用户数据失败", e);
  }
  const local = (await ensureBaselineProfile()) || {};
  applyProfile(local);
}

function goProfileDetail() {
  if (!hasBaselineBound.value) {
    if (!hasConsent()) {
      router.push("/consent");
      return;
    }
    router.push("/baseline");
    return;
  }
  router.push("/my/profile");
}

function goBehaviorDetail() {
  router.push("/my/behavior");
}

function goConsentView() {
  router.push({ path: "/consent", query: { mode: "view" } });
}

async function onRevokeConsent() {
  if (!consented.value || revoking.value) return;
  try {
    await ElMessageBox.confirm(
      "确认撤回知情同意与隐私授权？撤回后将停止新的数据采集，再次使用需重新同意。",
      "撤回授权",
      {
        confirmButtonText: "确认撤回",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }
  const at = Date.now();
  revoking.value = true;
  trackEvent("consent", "revoke");
  try {
    const data = await recordRevokeLog({ source: "my", page: "my" }, at);
    applyConsentFromServer({
      has_consent: false,
      status: "revoke",
      at: data.at || at,
    });
  } catch (e) {
    console.warn("记录撤回授权失败", e);
    applyConsentFromServer({ has_consent: false, status: "revoke", at });
  } finally {
    invalidateOnboardingGate();
    consented.value = false;
    revoking.value = false;
    ElMessage.success("已撤回授权");
    router.replace("/consent");
  }
}

async function exitStudy() {
  try {
    await ElMessageBox.confirm(
      "确认解绑研究编号（再次登录时需要重新知情同意并绑定研究编号），清除本地数据并退出？",
      "退出研究",
      {
        confirmButtonText: "确认退出",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }
  exiting.value = true;
  const at = Date.now();
  trackEvent("my", "exit_study");
  try {
    await recordExitLog({ source: "my", page: "my" }, at);
  } catch (e) {
    console.warn("记录退出研究失败", e);
  }
  try {
    await logoutSession();
  } catch {
    clearAuth();
  }
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
  exiting.value = false;
  router.replace("/login");
}

async function logout() {
  if (loggingOut.value) return;
  loggingOut.value = true;
  try {
    await logoutSession();
  } finally {
    loggingOut.value = false;
    router.replace("/login");
  }
}

onMounted(async () => {
  await ensureLogin();
  trackEvent("my", "view");
  refresh();
});
</script>

<style scoped>
.page-my {
  width: 100%;
  margin: 0 auto;
  padding-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.profile-container {
  display: flex;
  flex-direction: row;
  gap: 16px;
}
.button-container {
  display: flex;
  flex-direction: row;
  gap: 60px;
  flex: 1;
  margin-top: 30px;
  justify-content: center;
}
.profile-card {
  width: 50%;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #eef0f2;
}

.profile-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.profile-more {
  border: none;
  background: transparent;
  color: #07c160;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.profile-more-arrow {
  font-size: 14px;
  line-height: 1;
}

.profile-id {
  font-size: 18px;
  font-weight: 600;
  color: #222;
  line-height: 1.4;
  margin: 0 0 4px;
}

.kv-list {
  margin-top: 4px;
}

.kv-card .profile-row {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f4;
  gap: 12px;
}

.kv-card .profile-row.is-last {
  border-bottom: none;
}

.kv-card .profile-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  text-align: center;
  line-height: 1.3;
  max-width: 120px;
}

.kv-card .label-researchId,
.kv-card .label-openCount {
  background: #ebe8ff;
  color: #df16ff;
}

.kv-card .label-age,
.kv-card .label-openCount {
  background: #e8f4ff;
  color: #1677ff;
}

.kv-card .label-grade,
.kv-card .label-missedDays {
  background: #fff3e0;
  color: #e65100;
}

.kv-card .label-major,
.kv-card .label-avgDiary {
  background: #f3e8ff;
  color: #7b1fa2;
}

.kv-card .label-gender,
.kv-card .label-avgVoice {
  background: #fce4ec;
  color: #c2185b;
}

.kv-card .label-onlyChild,
.kv-card .label-avgVideo {
  background: #e8f5e9;
  color: #2e7d32;
}

.kv-card .label-housing,
.kv-card .label-voiceSkips {
  background: #e0f7fa;
  color: #00838f;
}

.kv-card .label-videoSkips {
  background: #fff8e1;
  color: #f57f17;
}

.kv-card .label-checkinHours {
  background: #ede7f6;
  color: #5e35b1;
}

.kv-card .profile-value {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: #333;
  font-weight: 500;
  text-align: right;
  line-height: 1.5;
  word-break: break-word;
}

.kv-footnote {
  margin: 4px 0 0;
  font-size: 12px;
  color: #999;
  line-height: 1.5;
}

.profile-empty {
  margin: 0;
  font-size: 14px;
  color: #999;
  line-height: 1.6;
}

.btn-secondary,
.btn-revoke {
  display: block;
  width: 20%;
  height: 44px;
  margin-bottom: 12px;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
}

.btn-secondary {
  background: #fff;
  color: #07c160;
  border: 1px solid #07c160;
}

.btn-revoke {
  background: #fff;
  color: #304ccc;
  border: 1px solid #304ccc;
}

.btn-secondary:disabled,
.btn-revoke:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-exit {
  background: #fff;
  color: red;
  border: 1px solid red;
}
</style>
