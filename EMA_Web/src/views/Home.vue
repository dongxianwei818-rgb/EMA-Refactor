<template>
  <div class="page-home">
    <div class="hero-card">
      <el-card shadow="never" class="page-card hero-info">
        <h1 class="hero-title">
          心理健康 EMA
          <span class="hint2">{{ "(" + todayLabel + ")" }}</span>
        </h1>
        <p class="hero-subtitle">
          大学生心理健康风险连续监测与早期预警系统研究
        </p>
        <p class="hero-subtitle">
          问卷 + 文本 + 语音 + 视频 + 运动步数 + 使用行为分析
        </p>
        <p class="hero-subtitle2">
          消除回忆偏差、捕捉动态时序规律、高生态真实性
        </p>
        <p class="hero-subtitle2">支持情绪识别、行为模式分析、健康风险预警</p>
        <p class="hero-subtitle3">指导老师：***</p>
        <p class="hero-subtitle3">研究团队：***</p>
      </el-card>
      <el-card shadow="never" class="page-card hero-todo section-1">
        <template #header>
          <span>今日打卡进度</span>
        </template>
        <div class="progress-row">
          <span>{{ progress.done }} / {{ progress.total }}</span>
          <el-progress :percentage="progress.percent" :stroke-width="8" />
        </div>
        <el-button
          type="primary"
          class="start-btn"
          :loading="starting"
          @click="startFlow"
        >
          {{ checkinComplete ? "重新今日打卡" : "开始今日打卡" }}
        </el-button>
        <p v-if="checkinComplete" class="recheckin-hint">
          点击后，将重新开始今日打卡流程
        </p>
      </el-card>
    </div>
    <div class="task-list">
      <el-card
        v-for="(item, idx) in taskList"
        :key="item.key"
        shadow="hover"
        class="page-card task-card"
        :class="[{ 'task-card--active': item.canTap }, `section-${idx + 2}`]"
        @click="onTaskTap(item)"
      >
        <div class="task-head">
          <span class="task-name">{{ item.name }}</span>
          <el-tag
            size="small"
            :type="item.done ? 'success' : item.skip ? 'info' : 'warning'"
            effect="plain"
          >
            {{ item.done ? "已完成" : item.skip ? "跳过" : "待完成" }}
          </el-tag>
        </div>
        <p class="hint">{{ item.desc }}</p>
        <p v-if="item.canTap" class="tap-hint">点击开始此项</p>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessageBox } from "element-plus";
import { fetchDailyTasks } from "../api/ema";
import { isAdmin } from "../api/auth";
import { TASK_META } from "../constants/ema";
import {
  applyDailyTasksResponse,
  ensureCheckinSession,
  getNextTaskRoute,
  getTaskProgress,
  getTaskRoute,
  getTodayCheckinSessions,
  getTodayKey,
  getTodayTasks,
  isResearchBound,
  startRecheckin,
} from "../utils/ema";
import { hasConsent } from "../utils/consentState";
import { hydrateFromServer } from "../utils/hydrate";
import { markOnboardingSynced } from "../utils/onboardingGate";
import { trackEvent } from "../utils/tracker";

const router = useRouter();
const progress = ref({ done: 0, total: 5, percent: 0 });
const taskList = ref([]);
const checkinComplete = ref(false);
const sessionCount = ref(0);
const starting = ref(false);
const isAdminUser = isAdmin();

/** 预热打卡页 chunk，避免点「开始今日打卡」时白屏等待 */
function prefetchEmaChunks() {
  import("../layouts/TaskShell.vue");
  import("./ema/Questionnaire.vue");
  import("./ema/Diary.vue");
}

const todayLabel = computed(() => {
  const d = new Date();
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
});

function refresh() {
  const tasks = getTodayTasks();
  const prog = getTaskProgress();
  progress.value = prog;
  checkinComplete.value = prog.done >= prog.total;
  sessionCount.value = getTodayCheckinSessions().length;
  taskList.value = TASK_META.map((item) => {
    let skip = false;
    if (item.key === "voice" && tasks.voiceSkipped) skip = true;
    if (item.key === "video" && tasks.videoSkipped) skip = true;
    const done = !!tasks[item.key] && !skip;
    return {
      ...item,
      done,
      skip,
      canTap: !done && !skip,
    };
  });
}

function ensureReadyForCheckin() {
  if (!hasConsent()) {
    router.push("/consent");
    return false;
  }
  if (!isResearchBound()) {
    router.push("/baseline");
    return false;
  }
  return true;
}

async function navigateToNextTask(isRecheckin, sessionId) {
  const next = getNextTaskRoute();
  if (!next) {
    await ElMessageBox.alert("今日已完成全部任务", "提示", { type: "success" });
    return;
  }
  // 先跳转，会话与埋点放到后台，避免与路由抢主线程/网络
  const nav = router.push(next);
  const sid = sessionId || ensureCheckinSession();
  trackEvent("home", "start_flow", {
    sessionId: sid,
    recheckin: !!isRecheckin,
  });
  await nav;
}

async function startFlow() {
  if (starting.value) return;
  if (!ensureReadyForCheckin()) return;
  starting.value = true;
  try {
    if (checkinComplete.value) {
      try {
        await ElMessageBox.confirm("已经完成今日打卡，是否重新打卡？", "提示", {
          confirmButtonText: "重新打卡",
          cancelButtonText: "取消",
        });
        const sessionId = await startRecheckin();
        trackEvent("home", "recheckin_start", { sessionId });
        await navigateToNextTask(true, sessionId);
      } catch {
        /* cancelled */
      }
      return;
    }
    await navigateToNextTask(false);
  } finally {
    starting.value = false;
  }
}

async function onTaskTap(item) {
  if (!item.canTap || starting.value) return;
  if (!ensureReadyForCheckin()) return;
  const route = getTaskRoute(item.key);
  if (!route) return;
  starting.value = true;
  try {
    await router.push(route);
    ensureCheckinSession();
    trackEvent("home", "start_task", { task: item.key });
  } finally {
    starting.value = false;
  }
}

onMounted(async () => {
  if (isAdminUser) {
    trackEvent("home", "view", { admin: true });
    return;
  }
  if (!hasConsent()) {
    router.replace("/consent");
    return;
  }
  if (!isResearchBound()) {
    router.replace("/baseline");
    return;
  }
  // 首页已确认入组完成，延长门控新鲜度，避免进打卡页再等 /users/me
  markOnboardingSynced();
  prefetchEmaChunks();
  refresh();
  trackEvent("home", "view");
  try {
    await hydrateFromServer();
    const daily = await fetchDailyTasks(getTodayKey(), ensureCheckinSession());
    applyDailyTasksResponse(daily);
    refresh();
  } catch {
    /* 离线仍展示本地缓存 */
  }
});
</script>

<style scoped>
.page-home {
  width: 100%;
  display: flex;
  flex-direction: column;
}
.hero-card {
  display: flex;
  flex-direction: row;
  gap: 16px;
  flex: 1;
  max-height: 250px;
}
.hero-info {
  flex-direction: row;
  gap: 16px;
  flex: 1;
  background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%);
}
.hero-todo {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}
.task-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  width: 100%;
}

.page-card {
  margin-bottom: 16px;
  border-radius: 16px;
}

.hero-title {
  margin: 0 0 8px;
  font-size: 28px;
  color: #75eed7;
}
.hero-subtitle {
  font-size: 16px;
  color: #c6e2ff;
  margin: 0;
  line-height: 1.6;
}
.hero-subtitle2 {
  font-size: 16px;
  color: #75eed7;
  margin: 0;
  line-height: 1.6;
}
.hero-subtitle3 {
  font-size: 14px;
  color: #67c23a;
  margin: 0;
  line-height: 1.6;
}
.hint {
  color: #909399;
  line-height: 1.6;
  margin: 0;
}
.hint2 {
  color: #d8e639;
  line-height: 1.6;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.progress-row {
  margin-bottom: 16px;
}

.start-btn {
  width: 100%;
  background: #07c160;
  border: 0;
}

.recheckin-hint {
  text-align: center;
  font-size: 12px;
  color: #f89898;
  margin-top: 8px;
  margin-bottom: 0;
}

.task-card {
  margin-bottom: 0;
  width: auto;
  min-width: 0;
  cursor: pointer;
  border-radius: 16px;
  border: 1px solid #e0e0e0;
  height: 100%;
}

.section-1 {
  border-left: 4px solid #1677ff;
}
.section-2 {
  border-left: 4px solid #722ed1;
}
.section-3 {
  border-left: 4px solid #fa8c16;
}
.section-4 {
  border-left: 4px solid #76de26;
}
.section-5 {
  border-left: 4px solid #f30698;
}
.section-6 {
  border-left: 4px solid #13c2c2;
}

.task-card--active {
  cursor: pointer;
  border-color: #fab6b6;
}

.task-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-name {
  font-weight: 600;
}

.tap-hint {
  color: #07c160;
  font-size: 12px;
  margin: 8px 0 0;
}
</style>
