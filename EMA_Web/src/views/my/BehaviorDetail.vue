<template>
  <div class="page-detail">
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
      <h1 class="nav-title">使用行为详情</h1>
      <span class="nav-spacer" />
    </header>

    <section v-if="hasData" class="card">
      <div v-for="section in sections" :key="section.id" class="detail-block">
        <h3 class="section-title">{{ section.title }}</h3>
        <div v-for="row in section.rows" :key="row.label" class="profile-row">
          <span class="profile-label">{{ row.label }}</span>
          <span class="profile-value">{{ row.value }}</span>
        </div>
      </div>
    </section>
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
.back-link {
  border: none;
  background: transparent;
  color: #0f6e5c;
  font-size: 14px;
  margin-bottom: 12px;
  cursor: pointer;
  padding: 0;
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

.card {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #eef0f2;
}

.detail-block + .detail-block {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #f0f2f4;
}

.section-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 700;
  color: #222;
}

.profile-row {
  display: flex;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid #f0f2f4;
}

.profile-row:last-child {
  border-bottom: none;
}

.profile-label {
  flex: 1;
  font-size: 14px;
  color: #666;
  padding-right: 12px;
}

.profile-value {
  max-width: 55%;
  font-size: 14px;
  color: #333;
  font-weight: 500;
  text-align: right;
  word-break: break-word;
}

.profile-empty {
  margin: 0;
  color: #999;
  font-size: 14px;
}
</style>
