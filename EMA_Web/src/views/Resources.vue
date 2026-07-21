<template>
  <div class="page-resources">
    <div class="resources-grid">
      <div class="resources-banner resources-cell">
        <div class="resources-banner-left">
          <div class="resources-banner-title">心理健康资源</div>
          <div class="resources-banner-sub">求助热线、校内支持与自助练习</div>
          <div class="resources-banner-sub">学校心理中心、热线、预约方式</div>
          <div class="resources-banner-sub">快速搭建标准化心理服务体系</div>
          <div class="resources-banner-sub">
            搭建多层级危机干预网络，降低极端心理事件发生率
          </div>
        </div>
        <div class="resources-banner-right">
          <div class="resources-banner-title">打破时空限制，降低求助门槛</div>
          <div class="resources-banner-sub">全场景随时获取服务</div>
          <div class="resources-banner-sub">服务分层适配不同人群</div>
          <div class="resources-banner-sub">数据互通，不用重复填报信息</div>
          <div class="resources-banner-sub">跨场景风险联动预警</div>
        </div>
      </div>

      <section
        v-for="(section, idx) in sections"
        :key="section.title"
        class="card resources-section resources-cell"
        :class="`resources-section-${idx + 1}`"
      >
        <h3 class="section-title">{{ section.title }}</h3>
        <p v-if="section.hint" class="section-hint">{{ section.hint }}</p>

        <div
          v-for="(resource, idx) in section.items"
          :key="`${section.title}-${idx}`"
          class="resource-item"
        >
          <div class="resource-main">
            <div class="resource-name">{{ resource.name }}</div>
            <div class="resource-desc">{{ formatDesc(resource) }}</div>
          </div>
          <a
            v-if="resource.phone"
            class="resource-action"
            :href="`tel:${resource.phone}`"
            @click="onCall(resource.phone)"
          >
            拨打
          </a>
          <button
            v-else-if="resource.copyText"
            type="button"
            class="resource-action resource-action-copy"
            @click="onCopy(resource.copyText)"
          >
            复制
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { ElMessage } from "element-plus";
import { RESOURCE_SECTIONS } from "../constants/resources";
import { trackEvent } from "../utils/tracker";

const sections = RESOURCE_SECTIONS;

function formatDesc(resource) {
  if (resource.phone)
    return `${resource.desc || ""} (${resource.phone})`.trim();
  return resource.desc || "";
}

function onCall(phone) {
  trackEvent("resources", "call", { phone });
}

async function onCopy(text) {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制");
    trackEvent("resources", "copy", { text });
  } catch {
    ElMessage.error("复制失败，请手动复制");
  }
}

onMounted(() => {
  trackEvent("resources", "view");
});
</script>

<style scoped>
.page-resources {
  width: 100%;
  margin: 0 auto;
  height: 100%;
  overflow: auto;
}

.resources-banner {
  background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
  border-radius: 16px;
  padding: 28px 24px;
  color: #fff;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  text-align: center;
  box-shadow: 0 8px 24px rgba(114, 46, 209, 0.22);
}
.resources-banner-left {
  width: 50%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: start;
  justify-content: center;
  text-align: center;
}
.resources-banner-right {
  width: 50%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: start;
  justify-content: center;
  text-align: center;
}

.resources-banner-title {
  font-size: 20px;
  font-weight: 700;
}

.resources-banner-sub {
  font-size: 13px;
  opacity: 0.88;
  margin-top: 8px;
  line-height: 1.5;
}

.resources-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: stretch;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 18px 18px 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #eef0f2;
}

.resources-cell {
  flex: 1 1 calc(50% - 8px);
  min-width: 0;
  box-sizing: border-box;
}

@media (max-width: 720px) {
  .resources-cell {
    flex: 1 1 100%;
  }
}

.section-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: #222;
}

.section-hint {
  margin: 0 0 4px;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.resource-item {
  display: flex;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #f0f2f4;
  gap: 12px;
}

.resource-item:last-child {
  border-bottom: none;
  padding-bottom: 6px;
}

.resource-main {
  flex: 1;
  min-width: 0;
}

.resource-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  line-height: 1.4;
}

.resource-desc {
  font-size: 13px;
  color: #888;
  line-height: 1.55;
  margin-top: 4px;
  word-break: break-word;
}

.resource-action {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  background: #07c160;
  color: #fff !important;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  border: none;
  cursor: pointer;
  line-height: 1;
}

.resource-action-copy {
  background: #fff;
  color: #07c160 !important;
  border: 1px solid #07c160;
}

.resources-section-1 {
  border-left: 4px solid #1677ff;
}
.resources-section-2 {
  border-left: 4px solid #722ed1;
}
.resources-section-3 {
  border-left: 4px solid #fa8c16;
}
.resources-section-4 {
  border-left: 4px solid #76de26;
}
.resources-section-5 {
  border-left: 4px solid #f30698;
}
.resources-section-6 {
  border-left: 4px solid #13c2c2;
}
</style>
