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

    <section v-if="hasBaselineBound" class="card">
      <p v-if="baselineTimeStr" class="baseline-time">
        基线测评完成时间：{{ baselineTimeStr }}
      </p>
      <div v-for="section in sections" :key="section.id" class="detail-block">
        <h3 class="section-title">{{ section.title }}</h3>
        <div
          v-for="(row, idx) in section.rows"
          :key="`${section.id}-${row.label}`"
          class="profile-row"
          :class="{ 'is-last': idx === section.rows.length - 1 }"
        >
          <span class="profile-label">{{ row.label }}</span>
          <span class="profile-value">{{ row.value }}</span>
        </div>
      </div>
      <p v-if="!sections.length" class="profile-empty">
        暂无已填写的档案字段。
      </p>
    </section>
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
import {
  buildProfileDetailSections,
  formatBaselineTime,
} from "../../utils/profile";

const hasBaselineBound = ref(false);
const sections = ref([]);
const baselineTimeStr = ref("");

onMounted(async () => {
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
  max-width: 720px;
  margin: 0 auto;
  padding-bottom: 24px;
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

.card {
  background: #fff;
  border-radius: 16px;
  padding: 16px 18px 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #eef0f2;
}

.baseline-time {
  margin: 0 0 8px;
  font-size: 13px;
  color: #999;
  line-height: 1.5;
}

.detail-block {
  margin-bottom: 4px;
}

.section-title {
  margin: 16px 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.detail-block:first-of-type .section-title {
  margin-top: 4px;
}

.profile-row {
  display: flex;
  align-items: flex-start;
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f4;
}

.profile-row.is-last {
  border-bottom: none;
}

.profile-label {
  flex: 1;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
  padding-right: 12px;
}

.profile-value {
  flex-shrink: 0;
  max-width: 55%;
  font-size: 14px;
  color: #333;
  font-weight: 500;
  text-align: right;
  line-height: 1.5;
  word-break: break-word;
}

.profile-empty {
  margin: 12px 0;
  color: #999;
  font-size: 14px;
  line-height: 1.6;
}
</style>
