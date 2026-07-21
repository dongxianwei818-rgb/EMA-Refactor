<template>
  <div class="consent-shell">
    <OnboardingHeader title="知情同意与隐私授权" />
    <div class="consent-page">
      <div class="consent-grid">
        <div v-if="isReview && hasAnswered" class="review-banner consent-cell">
          <h1 class="section-title">知情同意与隐私授权</h1>
          <div class="review-status">✓ 您已完成知情同意</div>
          <div class="review-time">同意时间：{{ consentTimeStr }}</div>
          <div class="review-hint">以下为当时阅读的内容，仅供查阅。</div>
        </div>

        <div
          v-if="isReview && !hasAnswered"
          class="review-banner review-banner--empty consent-cell"
        >
          <h1 class="section-title">知情同意与隐私授权</h1>
          <div class="review-status">✗ 您尚未完成知情同意</div>
          <div class="review-hint">请阅读并同意参与本研究</div>
        </div>

        <div
          v-for="(item, index) in sections"
          :key="item.title"
          class="card consent-card consent-cell"
          :style="{
            borderLeft: `4px solid ${sessionBorderColor(index)}`,
          }"
        >
          <div class="sec-title">{{ item.title }}</div>
          <p class="sec-body">{{ item.content }}</p>
        </div>
      </div>

      <div v-if="!isReview" class="footer">
        <label class="agree-row">
          <input type="checkbox" :checked="agreed" @change="toggleAgree" />
          <span>我已阅读并同意参与本研究</span>
        </label>
        <button
          class="btn-primary"
          :disabled="!agreed || submitting"
          @click="onConfirm"
        >
          {{ submitting ? "提交中…" : "同意并继续" }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="toast" class="toast">{{ toast }}</p>
      </div>

      <div v-else class="footer">
        <label class="agree-row agree-row--done">
          <input type="checkbox" checked disabled />
          <span>我已阅读并同意参与本研究</span>
        </label>
        <button class="btn-secondary" @click="onBack">返回</button>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import OnboardingHeader from "../components/OnboardingHeader.vue";
import { CONSENT_SECTIONS } from "../constants/consent";
import { fetchConsentStatus, recordAcceptLog } from "../api/consent";
import { ensureLogin } from "../api/auth";
import {
  acceptConsentLocal,
  applyConsentFromServer,
  getLocalConsent,
  hasConsent,
} from "../utils/consentState";
import { formatConsentTime } from "../utils/datetime";
import { markOnboardingSynced } from "../utils/onboardingGate";

const SESSION_BORDER_COLORS = [
  "#1677ff",
  "#722ed1",
  "#fa8c16",
  "#76de26",
  "#f30698",
  "#13c2c2",
  "#eb2f96",
  "#2f54eb",
  "#52c41a",
  "#fa541c",
];
const route = useRoute();
const router = useRouter();

const sections = CONSENT_SECTIONS;
const agreed = ref(false);
const isReview = computed(() => route.query.mode === "view");
const consentTimeStr = ref("");
const hasAnswered = ref(false);
const submitting = ref(false);
const error = ref("");
const toast = ref("");

function toggleAgree(e) {
  if (isReview.value) return;
  agreed.value = !!e.target.checked;
}

function sessionBorderColor(index) {
  const i = Number(index) || 0;
  return SESSION_BORDER_COLORS[i % SESSION_BORDER_COLORS.length];
}

async function initReviewMode() {
  error.value = "";
  try {
    await ensureLogin();
    const data = await fetchConsentStatus();
    applyConsentFromServer(data);
    if (data.has_consent && data.at) {
      hasAnswered.value = true;
      agreed.value = true;
      consentTimeStr.value = formatConsentTime(data.at);
      return;
    }
    hasAnswered.value = false;
    agreed.value = false;
    consentTimeStr.value = "";
  } catch {
    const record = getLocalConsent();
    if (record && record.at) {
      hasAnswered.value = true;
      agreed.value = true;
      consentTimeStr.value = formatConsentTime(record.at);
    } else {
      hasAnswered.value = false;
      agreed.value = false;
      consentTimeStr.value = "";
    }
  }
}

async function initOnboardingMode() {
  agreed.value = false;
  error.value = "";
  toast.value = "";
  try {
    await ensureLogin();
  } catch (e) {
    error.value = e.message || "登录失败";
    return;
  }

  try {
    const data = await fetchConsentStatus();
    applyConsentFromServer(data);
    if (data.has_consent) {
      router.replace("/baseline");
      return;
    }
  } catch {
    if (hasConsent()) {
      router.replace("/baseline");
    }
  }
}

function onConfirm() {
  if (isReview.value || !agreed.value || submitting.value) return;
  const at = Date.now();
  acceptConsentLocal(at);
  submitting.value = true;
  error.value = "";
  toast.value = "请继续完成基线测评";

  // 与小程序一致：本地先落盘，接口失败不阻断跳转
  recordAcceptLog({ source: "onboarding", page: "consent" }, at)
    .then((data) => {
      applyConsentFromServer({
        has_consent: true,
        status: "accept",
        at: data.at || at,
      });
      markOnboardingSynced();
    })
    .catch((err) => {
      console.warn("记录知情同意失败", err);
      applyConsentFromServer({ has_consent: true, status: "accept", at });
      markOnboardingSynced();
    });

  setTimeout(() => {
    submitting.value = false;
    router.replace("/baseline");
  }, 800);
}

function onBack() {
  if (window.history.length > 1) router.back();
  else router.push("/home");
}

function initByMode() {
  if (isReview.value) initReviewMode();
  else initOnboardingMode();
}

onMounted(initByMode);
watch(isReview, initByMode);
</script>

<style scoped>
.consent-shell {
  height: 100vh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #eef3f1;
}

.consent-page {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  width: 100%;
  margin: 0 auto;
  padding: 16px;
  overflow: hidden;
}

.consent-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  flex: 1;
  min-height: 0;
  align-content: flex-start;
  overflow-y: auto;
  padding-bottom: 8px;
}

.consent-cell {
  flex: 1 1 calc(50% - 8px);
  min-width: 0;
  box-sizing: border-box;
}

@media (max-width: 720px) {
  .consent-cell {
    flex: 1 1 100%;
  }
}

.section-title {
  margin: 0 0 16px;
  font-size: 22px;
  font-weight: 700;
  color: #1c2430;
}

.review-banner {
  background: #79bbff;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 0;
}

.review-banner--empty {
  background: #fff8e6;
  color: #996600;
  font-size: 14px;
}

.review-status {
  font-size: 16px;
  font-weight: 600;
  color: #c45656;
}

.review-time {
  font-size: 14px;
  color: #0606f3;
  margin-top: 6px;
}

.review-hint {
  font-size: 13px;
  color: #bc4d4d;
  margin-top: 6px;
}

.consent-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 0;
  box-shadow: 0 8px 24px rgba(28, 36, 48, 0.05);
  /* border: 1px solid #e8eee9; */
}

.sec-title {
  font-weight: 600;
  color: #07c160;
  margin-bottom: 8px;
  font-size: 15px;
}

.sec-body {
  margin: 0;
  font-size: 14px;
  color: #666;
  line-height: 1.7;
}

.footer {
  flex-shrink: 0;
  padding: 12px 0 8px;
  background: linear-gradient(to top, #eef3f1 70%, transparent);
  display: flex;
  justify-content: space-around;
}

.agree-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 14px;
  cursor: pointer;
}

.agree-row--done {
  color: #07c160;
}

.agree-row input {
  width: 18px;
  height: 18px;
  accent-color: #07c160;
}

.btn-primary,
.btn-secondary {
  width: 150px;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary {
  border: none;
  background: #07c160;
  color: #fff;
}

.btn-primary:disabled {
  background-color: #c8c8c8;
  cursor: not-allowed;
}

.btn-secondary {
  background: #fff;
  color: #07c160;
  border: 1px solid #07c160;
}

.error {
  color: #b42318;
  margin-top: 10px;
  font-size: 13px;
}

.toast {
  color: #07c160;
  margin-top: 10px;
  font-size: 13px;
}
</style>
