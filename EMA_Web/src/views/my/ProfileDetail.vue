<template>
  <div class="page-profile-detail">
    <header class="detail-nav">
      <button
        type="button"
        class="nav-back"
        aria-label="返回"
        @click="$router.push('/my')"
      >
        <span style="font-size: 16px; font-weight: 600; color: #0f6e5c"
          >‹ 返回</span
        >
      </button>
      <h1 class="nav-title">基本信息详情</h1>
      <span class="nav-spacer" />
    </header>

    <p v-if="hasBaselineBound && baselineTimeStr" class="baseline-time">
      基线测评完成时间：{{ baselineTimeStr }}
    </p>

    <div v-if="hasBaselineBound" class="profile-grid">
      <section
        v-for="(section, index) in sections"
        :key="section.id"
        class="card profile-cell"
        :style="{
          borderLeft: `4px solid ${sessionBorderColor(index)}`,
        }"
      >
        <h3 class="section-title">{{ section.title }}</h3>
        <div
          v-for="(row, idx) in section.rows"
          :key="`${section.id}-${row.id || row.label}`"
          class="profile-row"
          :class="{ 'is-last': idx === section.rows.length - 1 }"
        >
          <span
            class="profile-label"
            :class="row.id ? `label-${row.id}` : `label-idx-${idx % 6}`"
            >{{ row.label }}</span
          >
          <span class="profile-value">{{ row.value }}</span>
        </div>
      </section>
      <p v-if="!sections.length" class="profile-empty profile-cell">
        暂无已填写的档案字段。
      </p>
    </div>
    <section v-else class="card">
      <p class="profile-empty">尚未完成基线测评，暂无档案详情。</p>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import {
  ensureBaselineProfile,
  hasBaseline,
  isResearchBound,
} from "../../utils/ema";
import { getServerProfile } from "../../utils/consentState";
import { hydrateFromServer } from "../../utils/hydrate";
import {
  buildProfileDetailSections,
  formatBaselineTime,
} from "../../utils/profile";

const hasBaselineBound = ref(false);
const sections = ref([]);
const baselineTimeStr = ref("");
const SESSION_BORDER_COLORS = [
  "#1677ff",
  "#f30698",
  "#2f54eb",
  "#52c41a",
  "#fa541c",
  "#722ed1",
  "#fa8c16",
  "#76de26",
  "#13c2c2",
  "#eb2f96",
];
function sessionBorderColor(index) {
  const i = Number(index) || 0;
  return SESSION_BORDER_COLORS[i % SESSION_BORDER_COLORS.length];
}
onMounted(async () => {
  try {
    await hydrateFromServer();
  } catch {
    /* ignore */
  }
  const local = (await ensureBaselineProfile()) || {};
  const server = getServerProfile() || {};
  const profile = {
    ...local,
    researchId:
      local.researchId || local.research_id || server.research_id || "",
  };
  hasBaselineBound.value = isResearchBound() || hasBaseline();
  sections.value = buildProfileDetailSections(profile);
  baselineTimeStr.value = formatBaselineTime(profile.at);
});
</script>

<style scoped>
.page-profile-detail {
  width: 100%;
  margin: 0 auto;
  height: 100%;
  overflow: auto;
}

.detail-nav {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  min-height: 36px;
}

.nav-back {
  width: auto;
  height: 36px;
  border: none;
  background: transparent;
  color: #333;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-title {
  flex: 1;
  margin: 0;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #222;
}

.nav-spacer {
  width: 36px;
}

.baseline-time {
  margin: 0 0 16px;
  font-size: 13px;
  color: #999;
  line-height: 1.5;
}

.profile-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: stretch;
  align-content: flex-start;
}

.profile-cell {
  flex: 0 1 calc(50% - 8px);
  width: calc(50% - 8px);
  max-width: calc(50% - 8px);
  min-width: 0;
  box-sizing: border-box;
}

@media (max-width: 720px) {
  .profile-cell {
    flex: 0 1 100%;
    width: 100%;
    max-width: 100%;
  }
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 16px 18px 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  /* border: 1px solid #eef0f2; */
}

.section-title {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.profile-row {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f4;
  gap: 12px;
}

.profile-row.is-last {
  border-bottom: none;
}

.profile-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  text-align: center;
  line-height: 1.3;
  max-width: 48%;
  background: #f5f5f5;
  color: #666;
}

.profile-value {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: #333;
  font-weight: 500;
  text-align: right;
  line-height: 1.5;
  word-break: break-word;
}

.label-researchId,
.label-idx-0 {
  background: #e8f4ff;
  color: #1677ff;
}

.label-age,
.label-course_pressure,
.label-sleep_habit,
.label-phq9_1,
.label-idx-1 {
  background: #e8f4ff;
  color: #1f477f;
}

.label-grade,
.label-exam_pressure,
.label-exercise_freq,
.label-phq9_2,
.label-idx-2 {
  background: #fff3e0;
  color: #e65100;
}

.label-major,
.label-gpa_pressure,
.label-social_freq,
.label-gad7_1,
.label-idx-3 {
  background: #f3e8ff;
  color: #7b1fa2;
}

.label-gender,
.label-job_pressure,
.label-gad7_2,
.label-idx-4 {
  background: #fce4ec;
  color: #c2185b;
}

.label-onlyChild,
.label-pss_1,
.label-counsel_before,
.label-idx-5 {
  background: #e8f5e9;
  color: #2e7d32;
}

.label-housing,
.label-pss_2,
.label-treatment_now,
.label-isi_1,
.label-ucla_1,
.label-self_harm {
  background: #e0f7fa;
  color: #00838f;
}

.profile-empty {
  margin: 12px 0;
  color: #999;
  font-size: 14px;
  line-height: 1.6;
}
</style>
