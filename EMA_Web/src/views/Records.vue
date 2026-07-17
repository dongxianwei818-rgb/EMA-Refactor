<template>
  <div class="page-records">
    <el-skeleton v-if="loading" :rows="6" animated />
    <el-alert
      v-else-if="error"
      type="error"
      :title="error"
      show-icon
      :closable="false"
    />

    <template v-else>
      <div v-if="sessions.length" class="records-summary">
        <div class="records-summary-count">{{ sessions.length }}</div>
        <div class="records-summary-label">次打卡记录</div>
        <div class="records-summary-sub">共 {{ totalCount }} 条采集项</div>
      </div>

      <div v-else class="records-empty">
        <p class="records-empty-title">暂无采集记录</p>
        <p class="records-empty-hint">
          完成 EMA 打卡后，问卷、日记、语音等采集项将在此按会话展示。
        </p>
      </div>

      <article
        v-for="session in sessions"
        :key="session.key"
        class="session-group"
        :class="{ 'is-expanded': expandedKey === session.key }"
      >
        <header class="session-header" @click="toggleSession(session.key)">
          <div class="session-header-left">
            <span class="session-badge">第 {{ session.sessionId }} 次打卡</span>
            <h2 class="session-date">{{ session.dateLabel }}</h2>
          </div>
          <div class="session-header-right">
            <div class="session-count">{{ session.itemCount }} 项</div>
            <div class="session-time">{{ session.timeRange }}</div>
            <span class="session-chevron" aria-hidden="true">{{
              expandedKey === session.key ? "▴" : "▾"
            }}</span>
          </div>
        </header>

        <div v-show="expandedKey === session.key" class="session-body">
          <div
            v-for="record in session.items"
            :key="record.id"
            class="record-item"
          >
            <span class="record-item-type" :class="`type-${record.type}`">
              {{ record.typeLabel }}
            </span>
            <div class="record-item-main">
              <p class="record-item-summary">{{ record.summary }}</p>
              <p class="record-item-time">{{ record.timeLabel }}</p>
            </div>
          </div>
        </div>
      </article>
    </template>
  </div>
</template>

<script setup>
import { onActivated, onMounted, ref } from "vue";
import { ensureLogin } from "../api/auth";
import { loadRecordSessions } from "../utils/records";
import { trackEvent } from "../utils/tracker";

const loading = ref(true);
const error = ref("");
const sessions = ref([]);
const totalCount = ref(0);
/** 手风琴：同时最多展开一条；默认最近一条 */
const expandedKey = ref("");
let tracked = false;

function refresh() {
  const data = loadRecordSessions();
  sessions.value = data.sessions;
  totalCount.value = data.totalCount;
  const keys = new Set(data.sessions.map((s) => s.key));
  if (!expandedKey.value || !keys.has(expandedKey.value)) {
    expandedKey.value = data.sessions[0]?.key || "";
  }
}

function toggleSession(key) {
  expandedKey.value = expandedKey.value === key ? "" : key;
}

async function loadPage() {
  loading.value = true;
  error.value = "";
  try {
    await ensureLogin();
    if (!tracked) {
      trackEvent("records", "view");
      tracked = true;
    }
    refresh();
  } catch (e) {
    error.value = e.message || String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(loadPage);
onActivated(refresh);
</script>

<style scoped>
.page-records {
  max-width: 720px;
  margin: 0 auto;
  padding-bottom: 24px;
}

.records-summary {
  background: linear-gradient(
    135deg,
    #f09cb5 0%,
    #ce31e6 20%,
    #0619ed 50%,
    #0f6e5c 70%,
    #49b968 100%
  );
  border-radius: 16px;
  padding: 28px 24px;
  margin-bottom: 20px;
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 8px 24px rgba(15, 110, 92, 0.22);
}

.records-summary-count {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.1;
}

.records-summary-label {
  font-size: 18px;
  font-weight: 600;
  margin-top: 6px;
}

.records-summary-sub {
  font-size: 13px;
  opacity: 0.88;
  margin-top: 10px;
}

.records-empty {
  text-align: center;
  padding: 72px 16px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #e8ece9;
}

.records-empty-title {
  margin: 0;
  font-size: 16px;
  color: #606266;
}

.records-empty-hint {
  margin: 10px 0 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.6;
}

.session-group {
  background: #fff;
  border-radius: 16px;
  margin-bottom: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #eef0f2;
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 18px 20px;
  background: #f7faf8;
  cursor: pointer;
  user-select: none;
}

.session-group.is-expanded .session-header {
  border-bottom: 1px solid #e8ece9;
}

.session-header-left {
  flex: 1;
  min-width: 0;
}

.session-badge {
  display: inline-block;
  background: #49b968;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 999px;
  line-height: 1.4;
}

.session-date {
  margin: 10px 0 0;
  font-size: 20px;
  font-weight: 600;
  color: #222;
  line-height: 1.3;
}

.session-header-right {
  text-align: right;
  flex-shrink: 0;
  margin-left: 16px;
  position: relative;
  padding-right: 18px;
}

.session-chevron {
  position: absolute;
  right: 0;
  top: 2px;
  font-size: 12px;
  color: #909399;
  line-height: 1;
}

.session-count {
  font-size: 15px;
  font-weight: 600;
  color: #0f6e5c;
}

.session-time {
  font-size: 12px;
  color: #888;
  margin-top: 6px;
}

.session-body {
  padding: 4px 0;
}

.record-item {
  display: flex;
  align-items: flex-start;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f2f4;
}

.record-item:last-child {
  border-bottom: none;
}

.record-item-type {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  margin-right: 12px;
  margin-top: 2px;
  max-width: 88px;
  text-align: center;
  line-height: 1.3;
}

.type-questionnaire {
  background: #e8f4ff;
  color: #1677ff;
}

.type-diary {
  background: #fff3e0;
  color: #e65100;
}

.type-voice {
  background: #f3e8ff;
  color: #7b1fa2;
}

.type-video {
  background: #fce4ec;
  color: #c2185b;
}

.type-steps {
  background: #e8f5e9;
  color: #2e7d32;
}

.record-item-main {
  flex: 1;
  min-width: 0;
}

.record-item-summary {
  margin: 0;
  font-size: 14px;
  color: #333;
  line-height: 1.55;
  word-break: break-word;
}

.record-item-time {
  margin: 6px 0 0;
  font-size: 12px;
  color: #aaa;
}
</style>
