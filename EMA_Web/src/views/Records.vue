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
      <div v-if="!sessions.length" class="records-empty">
        <p class="records-empty-title">暂无采集记录</p>
        <p class="records-empty-hint">
          完成 EMA 打卡后，问卷、日记、语音等采集项将在此按会话展示。
        </p>
      </div>
      <template v-else>
        <div class="session-grid">
          <div class="records-summary">
            <div class="records-summary-left">
              <div class="records-summary-count">
                <div class="records-summary-label">
                  今日：{{ getTodayKey() }}
                </div>
                <div>
                  <span class="records-summary-label">共</span>
                  <span class="records-summary-count-number">{{
                    todaySessions.length
                  }}</span>
                  <span class="records-summary-label"> 次打卡记录</span>
                </div>
              </div>
              <div class="records-summary-sub">
                共
                <span class="records-summary-sub-number">{{
                  todaySessionsCount
                }}</span>
                条采集项
              </div>
            </div>
            <div class="records-summary-right">
              <div class="records-summary-count">
                <div class="records-summary-label">
                  {{ historyData + " 至今日(含当天)" }}
                </div>
                <span class="records-summary-label">共</span>
                <span class="records-summary-count-number">{{
                  sessions.length
                }}</span>
                <span class="records-summary-label"> 次打卡记录</span>
              </div>
              <div class="records-summary-sub">
                共
                <span class="records-summary-sub-number">{{ totalCount }}</span>
                条采集项
              </div>
            </div>
          </div>
          <article
            v-for="(session, idx) in visibleSessions"
            :key="session.key"
            class="session-group"
            :class="{ 'is-expanded': expandedKey === session.key }"
            :style="{
              borderLeft: `4px solid ${sessionBorderColor(idx)}`,
            }"
          >
            <header class="session-header" @click="toggleSession(session.key)">
              <div class="session-header-left">
                <span class="session-badge"
                  >第 {{ session.sessionId }} 次打卡</span
                >
                <h2 class="session-date">{{ session.dateLabel }}</h2>
                <h3 class="session-date2">共{{ session.itemCount }}条采集项</h3>
                <h3 class="session-date2-link">点击查看详情</h3>
              </div>
              <div class="session-header-right">
                <div class="session-count">{{ session.itemCount }} 项</div>
                <div class="session-time">{{ session.timeRange }}</div>
                <span class="session-chevron" aria-hidden="true">
                  <el-icon>
                    <ArrowUp v-if="expandedKey === session.key" />
                    <ArrowDown v-else />
                  </el-icon>
                </span>
              </div>
            </header>

            <div
              v-show="expandedKey === session.key"
              class="session-body"
              @click.stop
            >
              <p v-if="!session.items.length" class="session-body-empty">
                本轮打卡尚未提交采集项，完成任务后将显示在此。
              </p>
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

          <button
            v-if="showMoreCard"
            type="button"
            class="session-group session-more"
            @click="showAllSessions = true"
          >
            <span class="session-more-title">显示更多</span>
            <span class="session-more-sub"
              >还有 {{ sessions.length - SESSION_PREVIEW_LIMIT }} 条记录</span
            >
          </button>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { onActivated, onMounted, ref, computed } from "vue";
import { ArrowDown, ArrowUp } from "@element-plus/icons-vue";
import { ensureLogin } from "../api/auth";
import { hydrateFromServer } from "../utils/hydrate";
import { loadRecordSessions } from "../utils/records";
import { getTodayKey } from "../utils/ema";
import { trackEvent } from "../utils/tracker";

const loading = ref(true);
const error = ref("");
const sessions = ref([]);
const totalCount = ref(0);
/** 手风琴：同时最多展开一条；默认最近一条 */
const expandedKey = ref("");
const showAllSessions = ref(false);
const SESSION_PREVIEW_LIMIT = 10;
let tracked = false;

const visibleSessions = computed(() => {
  if (showAllSessions.value || sessions.value.length <= SESSION_PREVIEW_LIMIT) {
    return sessions.value;
  }
  return sessions.value.slice(0, SESSION_PREVIEW_LIMIT);
});

const showMoreCard = computed(
  () => !showAllSessions.value && sessions.value.length > SESSION_PREVIEW_LIMIT,
);

const todaySessions = computed(() => {
  const today = getTodayKey(); // yyyy-MM-dd
  return sessions.value.filter((session) => session.date === today);
});
const todaySessionsCount = computed(() => {
  let count = 0;
  for (var i = 0; i < todaySessions.value.length; i++) {
    count += todaySessions.value[i].items.length;
  }
  return count;
});

const historyData = computed(() => {
  const list = sessions.value.filter(
    (session) => session.date !== getTodayKey(),
  );
  let earliest = "";
  for (const session of list) {
    const d = session.date || "";
    if (!d) continue;
    if (!earliest || d < earliest) earliest = d;
  }
  return earliest;
});

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

/** 按列表顺序依次循环取色 */
function sessionBorderColor(index) {
  const i = Number(index) || 0;
  return SESSION_BORDER_COLORS[i % SESSION_BORDER_COLORS.length];
}

function refresh() {
  const data = loadRecordSessions();
  sessions.value = data.sessions;
  totalCount.value = data.totalCount;
  if (sessions.value.length <= SESSION_PREVIEW_LIMIT) {
    showAllSessions.value = false;
  }
  const keys = new Set(data.sessions.map((s) => s.key));
  // 展开态失效时收起，不自动展开（详情改为点击后浮动显示）
  if (expandedKey.value && !keys.has(expandedKey.value)) {
    expandedKey.value = "";
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
    await hydrateFromServer();
    refresh();
  } catch (e) {
    error.value = e.message || String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(loadPage);
onActivated(async () => {
  try {
    await hydrateFromServer();
  } catch {
    /* ignore */
  }
  refresh();
});
</script>

<style scoped>
.page-records {
  width: 100%;
  height: 100%;
  min-height: 100%;
  margin: 0 auto;
  box-sizing: border-box;
  overflow: auto;
}

.records-summary {
  background: #337ecc;
  border-radius: 16px;
  padding: 20.5px;
  color: #fff;
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  align-items: center;
  box-shadow: 0 8px 24px rgba(15, 110, 92, 0.22);
}
.records-summary-left {
  width: 50%;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.records-summary-right {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
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
.records-summary-count-number {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.1;
}
.records-summary-sub-number {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
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

.session-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  width: 100%;
  align-items: start;
}

.session-group {
  position: relative;
  background: #fff;
  border-radius: 16px;
  margin-bottom: 0;
  overflow: visible;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #eef0f2;
  min-width: 0;
  z-index: 1;
}

.session-group.is-expanded {
  z-index: 40;
}

.session-more {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 88px;
  padding: 22px 14px;
  cursor: pointer;
  border: 1px dashed #c5d0cb;
  background: #f7faf8;
  color: #0f6e5c;
  font: inherit;
  box-shadow: none;
}

.session-more:hover {
  border-color: #0f6e5c;
  background: #eef7f3;
}

.session-more-title {
  font-size: 16px;
  font-weight: 600;
}

.session-more-sub {
  font-size: 13px;
  color: #909399;
}

@media (max-width: 720px) {
  .session-grid {
    grid-template-columns: 1fr;
  }
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 22px 14px;
  background: #f7faf8;
  cursor: pointer;
  user-select: none;
  border-radius: 16px;
}

.session-group.is-expanded .session-header {
  border-bottom: 1px solid #e8ece9;
  border-radius: 16px 16px 0 0;
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
  line-height: 1.1;
}
.session-date2 {
  margin: 0 0 0;
  font-size: 14px;
  font-weight: 400;
  color: #909399;
  line-height: 1.1;
  margin-top: 5px;
}
.session-date2-link {
  margin-top: 10px;
  font-size: 16px;
  font-weight: 400;
  color: #409eff;
  cursor: pointer;
  margin-bottom: 0;
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
  color: #909399;
  display: inline-flex;
  align-items: center;
  line-height: 1;
}

.session-chevron .el-icon {
  font-size: 14px;
}

.session-count {
  font-size: 15px;
  font-weight: 600;
  color: #49b968;
}

.session-time {
  margin: 20px 0 0;
  font-size: 20px;
  font-weight: 600;
  color: #222;
  line-height: 1.3;
}

.session-body {
  position: absolute;
  left: -1px;
  right: -1px;
  top: 100%;
  z-index: 50;
  margin-top: -1px;
  padding: 4px 0;
  background: #fff;
  border: 1px solid #eef0f2;
  border-top: none;
  border-radius: 0 0 16px 16px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.12);
  max-height: min(420px, 60vh);
  overflow-y: auto;
}

.session-body-empty {
  margin: 0;
  padding: 16px 20px;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
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
