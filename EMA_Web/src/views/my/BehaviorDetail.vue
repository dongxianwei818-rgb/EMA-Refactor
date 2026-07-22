<template>
  <div class="page-detail">
    <header class="detail-nav">
      <button
        type="button"
        class="nav-back"
        aria-label="返回"
        @click="$router.push('/my')"
      >
        <span class="nav-back-text">‹ 返回</span>
      </button>
      <h1 class="nav-title">使用行为详情</h1>
      <span class="nav-spacer" />
    </header>

    <div v-if="hasData" class="profile-grid">
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
          :key="`${section.id}-${row.id || row.label}-${idx}`"
          class="profile-row"
          :class="{ 'is-last': idx === section.rows.length - 1 }"
        >
          <span class="profile-label" :class="labelClass(row, idx)">{{
            row.label
          }}</span>
          <span class="profile-value">{{ row.value }}</span>
        </div>
      </section>
      <p v-if="!sections.length" class="profile-empty profile-cell">
        暂无使用行为记录。
      </p>
    </div>
    <section v-else class="card">
      <p class="profile-empty">暂无使用行为记录。</p>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { buildBehaviorDetailSections } from "../../utils/behavior";
import { hydrateFromServer } from "../../utils/hydrate";
import { trackEvent } from "../../utils/tracker";

const sections = ref([]);
const hasData = ref(false);

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

const SUMMARY_LABEL_IDS = new Set([
  "total",
  "openCount",
  "todaySessions",
  "missedDays",
  "recheckinCount",
  "avgDiary",
  "avgVoice",
  "avgVideo",
  "voiceSkips",
  "videoSkips",
]);

/** 概览用固定色；模块等其余行按序号循环彩色标签 */
function labelClass(row, idx) {
  if (row.id && SUMMARY_LABEL_IDS.has(row.id)) return `label-${row.id}`;
  return `label-idx-${idx % 6}`;
}

onMounted(async () => {
  trackEvent("my", "behavior_detail_view");
  try {
    await hydrateFromServer();
  } catch {
    /* ignore */
  }
  const detail = buildBehaviorDetailSections();
  sections.value = detail.sections;
  hasData.value = detail.sections.length > 0 || detail.logs.length > 0;
});
</script>

<style scoped>
.page-detail {
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
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.nav-back-text {
  display: inline-flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #0f6e5c;
  line-height: 36px;
}

.nav-title {
  flex: 1;
  margin: 0;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #222;
  line-height: 36px;
}

.nav-spacer {
  width: 36px;
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

.label-total,
.label-openCount,
.label-idx-0 {
  background: #e8f4ff;
  color: #1677ff;
}

.label-todaySessions,
.label-missedDays,
.label-idx-1 {
  background: #fff3e0;
  color: #e65100;
}

.label-recheckinCount,
.label-avgDiary,
.label-idx-2 {
  background: #f3e8ff;
  color: #7b1fa2;
}

.label-avgVoice,
.label-idx-3 {
  background: #fce4ec;
  color: #c2185b;
}

.label-avgVideo,
.label-voiceSkips,
.label-idx-4 {
  background: #e8f5e9;
  color: #2e7d32;
}

.label-videoSkips,
.label-idx-5 {
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
