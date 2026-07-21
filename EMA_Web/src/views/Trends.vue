<template>
  <div class="page-trends">
    <el-skeleton v-if="loading" :rows="8" animated />
    <el-alert
      v-else-if="error"
      type="error"
      :title="error"
      show-icon
      :closable="false"
    />

    <template v-else>
      <div
        class="trends-hero-row"
        :class="{ 'trends-hero-row--split': showRisk }"
      >
        <div class="trends-summary" :class="summaryClass">
          <div class="trends-summary-left">
            <div class="trends-summary-title" v-html="summaryTitle"></div>
            <div class="trends-summary-sub">{{ summarySub }}</div>
            <div class="trends-summary-sub" v-html="summarySub2"></div>
          </div>
          <div class="trends-summary-right">
            <div>风险指数范围是 0–15（与现有风险评估的风险指数一致）</div>
            <div
              class="risk-summary"
              style="margin-top: 10px; margin-bottom: 10px"
            >
              <span class="modality-summary-low">低风险：0–4</span>
              <span class="modality-summary-medium">中等关注：5–9</span>
              <span class="modality-summary-high">需重点关注：10–15</span>
            </div>
            <div style="opacity: 0.88">
              <p style="margin: 3px 0; font-size: 13px">
                五模态各自的分数也是同一套 0–15刻度
              </p>
              <p style="margin: 3px 0; font-size: 13px">
                当日有数据的模态按权重加权平均后得到「融合指数」。
              </p>
              <p style="margin: 3px 0; font-size: 13px">
                进度条宽度按 分数 / 15 计算。
              </p>
            </div>
          </div>
        </div>

        <template v-if="showRisk">
          <div v-if="!risk.hasAssessment" class="trends-empty">
            完成基线测评或 EMA 打卡后，将展示风险评估与预测信息
          </div>

          <section v-else class="trends-section card risk-card">
            <span class="panel-tag">01</span>
            <h3 class="section-title">当前风险评估</h3>
            <div class="risk-level-row">
              <span class="risk-badge" :class="current.levelClass">{{
                current.levelLabel
              }}</span>
              <div class="risk-meta">
                <span class="risk-score"
                  >风险指数 {{ current.score ?? "--" }}</span
                >
                <span class="risk-updated">{{
                  current.updatedLabel || ""
                }}</span>
              </div>
            </div>
            <p class="risk-summary">{{ current.summary || "暂无摘要" }}</p>
            <div v-if="current.factors?.length" class="risk-factors">
              <div
                v-for="item in current.factors"
                :key="item.label"
                class="risk-factor"
              >
                <span class="risk-factor-label">{{ item.label }}</span>
                <span class="risk-factor-value">{{ item.value }}</span>
                <span class="risk-factor-source">{{ item.source }}</span>
              </div>
            </div>
          </section>
        </template>
      </div>

      <div v-if="showRisk && risk.hasAssessment" class="trends-detail-row">
        <section class="trends-section card forecast-card">
          <span class="panel-tag panel-tag--forecast">02</span>
          <h3 class="section-title">未来 7 天风险预测</h3>
          <div class="forecast-head">
            <div class="forecast-trend">
              <span class="forecast-trend-label">趋势走向</span>
              <span class="forecast-trend-value">{{
                forecast.trendLabel || "—"
              }}</span>
            </div>
            <span class="risk-badge" :class="forecast.peakLevelClass">
              {{ forecast.peakLevelLabel || "待评估" }}
            </span>
          </div>
          <p class="risk-summary">{{ forecast.summary || "" }}</p>
          <div v-if="forecast.days?.length" class="forecast-chart">
            <div
              v-for="day in forecast.days"
              :key="day.dayIndex"
              class="forecast-day"
            >
              <span class="forecast-date">{{ day.dateLabel }}</span>
              <div class="forecast-bar-wrap">
                <div
                  class="forecast-bar"
                  :class="`forecast-bar-${day.level}`"
                  :style="{ width: `${day.barWidth || 0}%` }"
                />
              </div>
              <span class="forecast-score">{{ day.score }}</span>
            </div>
          </div>
          <div class="forecast-legend">
            <span class="legend-item legend-low">低</span>
            <span class="legend-item legend-medium">中</span>
            <span class="legend-item legend-high">高</span>
          </div>
        </section>

        <section class="trends-section card alert-card">
          <span class="panel-tag panel-tag--alert">03</span>
          <h3 class="section-title">个体异常预警</h3>
          <p v-if="!risk.alertCount" class="risk-no-alert">
            暂无异常信号，状态整体平稳。
          </p>
          <template v-else>
            <div class="alert-summary">
              <span class="alert-summary-total"
                >共 {{ risk.alertCount }} 条</span
              >
              <span
                v-if="risk.alertDangerCount"
                class="alert-summary-chip alert-summary-danger"
              >
                重点 {{ risk.alertDangerCount }}
              </span>
              <span
                v-if="risk.alertWarnCount"
                class="alert-summary-chip alert-summary-warn"
              >
                留意 {{ risk.alertWarnCount }}
              </span>
            </div>
            <div class="alert-list">
              <div
                v-for="item in risk.alerts || []"
                :key="item.id"
                class="alert-item"
                :class="`alert-${item.level}`"
              >
                <div class="alert-item-head">
                  <span class="alert-level-tag">{{
                    item.levelLabel ||
                    (item.level === "danger" ? "重点关注" : "需留意")
                  }}</span>
                  <span v-if="item.category" class="alert-category">{{
                    item.category
                  }}</span>
                </div>
                <div class="alert-title">{{ item.title }}</div>
                <div class="alert-desc">{{ item.desc }}</div>
                <div v-if="item.metric || item.source" class="alert-meta">
                  <span v-if="item.metric" class="alert-metric">{{
                    item.metric
                  }}</span>
                  <span v-if="item.source" class="alert-source">{{
                    item.source
                  }}</span>
                </div>
              </div>
            </div>
          </template>
        </section>

        <section class="trends-section card record-card">
          <span class="panel-tag panel-tag--record">04</span>
          <h3 class="section-title">打卡概况</h3>
          <div class="record-stats">
            <div
              v-for="item in recordStatItems"
              :key="item.key"
              class="record-stat"
            >
              <span class="record-stat-label">{{ item.label }}</span>
              <span class="record-stat-value">{{ item.value }}</span>
            </div>
          </div>
        </section>
      </div>

      <section v-if="showRisk" class="trends-section card modality-card">
        <span class="panel-tag panel-tag--modality">05</span>
        <h3 class="section-title">五项 EMA 特征预测趋势</h3>
        <div class="modality-summary">
          <div class="modality-summary-left">
            <div style="width: 50%">
              <p class="risk-summary">
                {{
                  modalityForecast.summary?.split(" ")[0] ||
                  "完成五项 EMA 采集后将展示特征融合预测。"
                }}
              </p>
            </div>
            <div
              class="modality-summary-score"
              :style="{
                color:
                  modalityForecast.currentScore >= 10
                    ? '#f5222d'
                    : 5 <= modalityForecast.currentScore &&
                        modalityForecast.currentScore <= 9
                      ? '#faad14'
                      : '#52c41a',
              }"
            >
              {{ modalityForecast.currentScore ?? "—" }}
            </div>
          </div>
        </div>

        <div class="modality-chips">
          <div
            v-for="item in modalityForecast.modalities || []"
            :key="item.id"
            class="modality-chip"
            :class="{
              'modality-chip--elevated': item.elevated,
              'modality-chip--empty': !item.hasData,
            }"
          >
            <span class="modality-chip-label">{{ item.label }}</span>
            <span class="modality-chip-score">
              {{ item.hasData ? item.score : "—" }}
            </span>
            <span class="modality-chip-flag">
              {{ !item.hasData ? "暂无" : item.elevated ? "偏高" : "平稳" }}
            </span>
          </div>
        </div>

        <div v-if="modalityForecast.hasPrediction" class="modality-panels">
          <div class="modality-panel">
            <div class="forecast-head">
              <div class="forecast-trend">
                <span class="forecast-trend-label">近 7 日融合指数</span>
                <span class="forecast-trend-value">
                  {{ modalityForecast.currentScore ?? "—" }}
                </span>
              </div>
              <span
                class="risk-badge"
                :class="modalityForecast.currentLevelClass"
              >
                {{ modalityForecast.currentLevelLabel || "待评估" }}
              </span>
            </div>
            <div class="forecast-chart">
              <div
                v-for="day in modalityForecast.history || []"
                :key="`hist-${day.date}`"
                class="forecast-day"
              >
                <span class="forecast-date">{{ day.dateLabel }}</span>
                <div class="forecast-bar-wrap">
                  <div
                    v-if="day.hasData"
                    class="forecast-bar"
                    :class="`forecast-bar-${day.level}`"
                    :style="{ width: `${day.barWidth || 0}%` }"
                  />
                  <span v-else class="trend-empty">—</span>
                </div>
                <span class="forecast-score">{{
                  day.hasData ? day.score : ""
                }}</span>
              </div>
            </div>
          </div>

          <div class="modality-panel">
            <div class="forecast-head">
              <div class="forecast-trend">
                <span class="forecast-trend-label">预测走向</span>
                <span class="forecast-trend-value"
                  >{{ modalityForecast.forecast?.trendLabel || "—"
                  }}<span class="risk-summary2 modality-forecast-summary">
                    ({{ modalityForecast.forecast?.summary || "" }})
                  </span></span
                >
              </div>
              <span
                class="risk-badge"
                :class="modalityForecast.forecast?.peakLevelClass"
              >
                {{ modalityForecast.forecast?.peakLevelLabel || "待评估" }}
              </span>
            </div>

            <div
              v-if="modalityForecast.forecast?.days?.length"
              class="forecast-chart"
            >
              <div
                v-for="day in modalityForecast.forecast.days"
                :key="`pred-${day.dayIndex}`"
                class="forecast-day"
              >
                <span class="forecast-date">{{ day.dateLabel }}</span>
                <div class="forecast-bar-wrap">
                  <div
                    class="forecast-bar"
                    :class="`forecast-bar-${day.level}`"
                    :style="{ width: `${day.barWidth || 0}%` }"
                  />
                </div>
                <span class="forecast-score">{{ day.score }}</span>
              </div>
            </div>
            <div class="forecast-legend">
              <span class="legend-item legend-low">低</span>
              <span class="legend-item legend-medium">中</span>
              <span class="legend-item legend-high">高</span>
            </div>
          </div>
        </div>

        <p v-else class="risk-no-alert">
          暂无足够的五项特征数据，完成问卷、日记、语音、视频、步数采集后将自动生成预测趋势。
        </p>
      </section>

      <section v-if="showRisk" class="trends-section card behavior-card">
        <span class="panel-tag panel-tag--behavior">06</span>
        <h3 class="section-title">行为特征预测趋势</h3>
        <div class="modality-summary">
          <div class="modality-summary-left">
            <div style="width: 50%">
              <p class="risk-summary">
                {{
                  behaviorForecast.summary?.split(" ")[0] ||
                  "完成五项 EMA 采集后将展示特征融合预测。"
                }}
              </p>
            </div>
            <div
              class="modality-summary-score"
              :style="{
                color:
                  behaviorForecast.currentScore >= 10
                    ? '#f5222d'
                    : 5 <= behaviorForecast.currentScore &&
                        behaviorForecast.currentScore <= 9
                      ? '#faad14'
                      : '#52c41a',
              }"
            >
              {{ behaviorForecast.currentScore ?? "—" }}
            </div>
          </div>
        </div>

        <div class="modality-chips">
          <div
            v-for="item in behaviorForecast.signals || []"
            :key="item.id"
            class="modality-chip behavior-chip"
            :class="{
              'modality-chip--elevated': item.elevated,
              'modality-chip--empty': !item.hasData,
            }"
          >
            <span class="modality-chip-label">{{ item.label }}</span>
            <span class="modality-chip-score">
              {{ item.hasData ? item.score : "—" }}
            </span>
            <span class="modality-chip-flag">
              {{ !item.hasData ? "暂无" : item.elevated ? "偏高" : "平稳" }}
            </span>
          </div>
        </div>

        <div v-if="behaviorForecast.hasPrediction" class="modality-panels">
          <div class="modality-panel">
            <div class="forecast-head">
              <div class="forecast-trend">
                <span class="forecast-trend-label">近 7 日行为指数</span>
                <span class="forecast-trend-value">
                  {{ behaviorForecast.currentScore ?? "—" }}
                </span>
              </div>
              <span
                class="risk-badge"
                :class="behaviorForecast.currentLevelClass"
              >
                {{ behaviorForecast.currentLevelLabel || "待评估" }}
              </span>
            </div>
            <div class="forecast-chart">
              <div
                v-for="day in behaviorForecast.history || []"
                :key="`beh-hist-${day.date}`"
                class="forecast-day"
              >
                <span class="forecast-date">{{ day.dateLabel }}</span>
                <div class="forecast-bar-wrap">
                  <div
                    v-if="day.hasData"
                    class="forecast-bar"
                    :class="`forecast-bar-${day.level}`"
                    :style="{ width: `${day.barWidth || 0}%` }"
                  />
                  <span v-else class="trend-empty">—</span>
                </div>
                <span class="forecast-score">{{
                  day.hasData ? day.score : ""
                }}</span>
              </div>
            </div>
          </div>

          <div class="modality-panel">
            <div class="forecast-head">
              <div class="forecast-trend">
                <span class="forecast-trend-label">预测走向</span>
                <span class="forecast-trend-value"
                  >{{ behaviorForecast.forecast?.trendLabel || "—" }}
                  <span class="risk-summary2 modality-forecast-summary">
                    {{ behaviorForecast.forecast?.summary || "" }}
                  </span></span
                >
              </div>
              <span
                class="risk-badge"
                :class="behaviorForecast.forecast?.peakLevelClass"
              >
                {{ behaviorForecast.forecast?.peakLevelLabel || "待评估" }}
              </span>
            </div>

            <div
              v-if="behaviorForecast.forecast?.days?.length"
              class="forecast-chart"
            >
              <div
                v-for="day in behaviorForecast.forecast.days"
                :key="`beh-pred-${day.dayIndex}`"
                class="forecast-day"
              >
                <span class="forecast-date">{{ day.dateLabel }}</span>
                <div class="forecast-bar-wrap">
                  <div
                    class="forecast-bar"
                    :class="`forecast-bar-${day.level}`"
                    :style="{ width: `${day.barWidth || 0}%` }"
                  />
                </div>
                <span class="forecast-score">{{ day.score }}</span>
              </div>
            </div>
            <div class="forecast-legend">
              <span class="legend-item legend-low">低</span>
              <span class="legend-item legend-medium">中</span>
              <span class="legend-item legend-high">高</span>
            </div>
          </div>
        </div>

        <p v-else class="risk-no-alert">
          暂无足够的行为特征数据，完成 EMA
          打卡并生成行为特征后将自动展示预测趋势。
        </p>
      </section>

      <div
        v-if="showRisk && showHistory && hasData && risk.hasAssessment"
        style="margin-bottom: 16px"
      >
        <span class="trends-divider-text">历史数据趋势</span>
      </div>

      <template v-if="showHistory">
        <div v-if="!hasData && !showRisk" class="trends-empty">
          完成 EMA 打卡后，将展示历史趋势数据
        </div>

        <div
          v-else-if="hasData && (metrics.length || stepsTrend.length)"
          class="trends-history-row"
        >
          <section
            v-for="(metric, index) in metrics"
            :key="metric.id"
            class="trends-section card"
            :class="`trends-section-${index + 1}`"
          >
            <h3 class="section-title">{{ metric.label }}（0–10）</h3>
            <div
              v-for="point in metric.points"
              :key="`${metric.id}-${point.dateLabel}`"
              class="trend-row"
            >
              <span class="trend-date">{{ point.dateLabel }}</span>
              <div class="trend-bar-wrap">
                <div
                  v-if="point.hasData"
                  class="trend-bar trend-bar-ema"
                  :style="{ width: `${point.barWidth || 0}%` }"
                />
                <span v-else class="trend-empty">—</span>
              </div>
              <span class="trend-value">{{
                point.hasData ? point.value : ""
              }}</span>
            </div>
          </section>

          <section
            v-if="stepsTrend.length"
            class="trends-section card trends-section-5"
          >
            <h3 class="section-title">运动步数</h3>
            <div class="steps-meta">
              <span>今日 {{ stepsAnalytics.today || 0 }} 步</span>
              <span>7 日均 {{ stepsAnalytics.avg7 || 0 }} 步</span>
              <span v-if="stepsAnalytics.baseline"
                >基线 {{ stepsAnalytics.baseline }} 步</span
              >
            </div>
            <div
              v-for="item in stepsTrend"
              :key="item.dateLabel"
              class="trend-row"
            >
              <span class="trend-date">{{ item.dateLabel }}</span>
              <div class="trend-bar-wrap">
                <div
                  v-if="item.hasData"
                  class="trend-bar trend-bar-steps"
                  :style="{ width: `${item.barWidth || 0}%` }"
                />
                <span v-else class="trend-empty">—</span>
              </div>
              <span class="trend-value">{{
                item.hasData ? item.steps : ""
              }}</span>
            </div>
          </section>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { ensureLogin } from "../api/auth";
import { fetchTrendsOverview } from "../api/ema";
import { trackEvent } from "../utils/tracker";

const props = defineProps({
  /** all | risk | history */
  mode: { type: String, default: "all" },
});

const loading = ref(true);
const error = ref("");
const hasData = ref(false);
const risk = ref({});
const modalityForecast = ref({});
const behaviorForecast = ref({});
const metrics = ref([]);
const stepsTrend = ref([]);
const stepsAnalytics = ref({});
const stats = ref({});

const current = computed(() => risk.value?.current || {});
const forecast = computed(() => risk.value?.forecast || {});
const showRisk = computed(() => props.mode === "all" || props.mode === "risk");
const showHistory = computed(
  () => props.mode === "all" || props.mode === "history",
);

const recordStatItems = computed(() => {
  const s = stats.value || {};
  const formatSec = (n) => `${s[n] ?? 0} 秒`;
  return [
    { key: "missedDays", label: "连续缺测", value: `${s.missedDays ?? 0} 天` },
    {
      key: "checkinDays",
      label: "打卡天数",
      value: `${s.checkinDays ?? 0} 天`,
    },
    {
      key: "completedSessions",
      label: "完成轮次",
      value: `${s.completedSessions ?? 0} 次`,
    },
    {
      key: "avgDiaryWords",
      label: "平均日记字数",
      value: `${s.avgDiaryWords ?? 0} 字`,
    },
    {
      key: "avgVoiceSec",
      label: "平均语音时长",
      value: formatSec("avgVoiceSec"),
    },
    {
      key: "avgVideoSec",
      label: "平均视频时长",
      value: formatSec("avgVideoSec"),
    },
    {
      key: "avgQuestionnaireSec",
      label: "平均问卷时长",
      value: formatSec("avgQuestionnaireSec"),
    },
    {
      key: "avgTaskSec",
      label: "平均任务耗时",
      value: formatSec("avgTaskSec"),
    },
    {
      key: "avgSteps",
      label: "平均步数",
      value: `${s.avgSteps ?? 0} 步`,
    },
    {
      key: "avgSteps7",
      label: "近7日均步数",
      value: `${s.avgSteps7 ?? 0} 步`,
    },
    { key: "openCount", label: "打开次数", value: `${s.openCount ?? 0} 次` },
    {
      key: "recheckinCount",
      label: "补打卡次数",
      value: `${s.recheckinCount ?? 0} 次`,
    },
    {
      key: "voiceSkips",
      label: "语音跳过",
      value: `${s.voiceSkips ?? 0} 次`,
    },
    {
      key: "videoSkips",
      label: "视频跳过",
      value: `${s.videoSkips ?? 0} 次`,
    },
  ];
});

const summaryTitle = computed(() => {
  if (props.mode === "history") return "趋势分析";
  return "心理健康趋势与风险";
});

const summarySub = computed(() => {
  if (props.mode === "history") return "EMA 指标 · 运动步数";
  return "当前评估 · 未来预测 · 异常预警 · 行为特征预测 · 历史趋势";
});
const summarySub2 = computed(() => {
  if (props.mode === "history") return "EMA 指标 · 运动步数";
  return "数字化 · AI 成为普惠服务核心载体</br> 需求分层清晰 · 细分赛道爆发</br> 开放能力 · 生态共建</br> 行业规范化洗牌 · 告别野蛮生长";
});

const summaryClass = computed(() => ({
  "trends-summary--risk": props.mode === "risk",
  "trends-summary--history": props.mode === "history",
}));

onMounted(async () => {
  loading.value = true;
  try {
    await ensureLogin();
    trackEvent(props.mode === "risk" ? "risk" : "trends", "view");
    const data = await fetchTrendsOverview(7);
    hasData.value = !!(data && (data.hasData || data.has_data));
    risk.value = data?.risk || {};
    modalityForecast.value =
      data?.modalityForecast || data?.modality_forecast || {};
    behaviorForecast.value =
      data?.behaviorForecast || data?.behavior_forecast || {};
    metrics.value = data?.metrics || [];
    stepsTrend.value = data?.stepsTrend || data?.steps_trend || [];
    stepsAnalytics.value = data?.stepsAnalytics || data?.steps_analytics || {};
    stats.value = data?.stats || {};
  } catch (e) {
    error.value = e.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page-trends {
  width: 100%;
  margin: 0 auto;
  height: 100%;
  overflow: auto;
}

.trends-hero-row {
  display: grid;
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}

.trends-hero-row--split {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.trends-summary {
  background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%);
  border-radius: 16px;
  padding: 28px 24px;
  margin-bottom: 0;
  color: #fff;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  box-shadow: 0 8px 24px rgba(22, 119, 255, 0.22);
}
.trends-summary-left {
  width: 45%;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.trends-summary-right {
  height: 100%;
  font-size: 14px;
  flex: 1;
}
.trends-hero-row .trends-empty,
.trends-hero-row .risk-card {
  margin-bottom: 0;
  height: 100%;
}

.trends-detail-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}

.trends-detail-row .trends-section {
  margin-bottom: 0;
  height: 100%;
  min-width: 0;
}

@media (max-width: 900px) {
  .trends-detail-row {
    grid-template-columns: 1fr;
  }
}

.trends-history-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}

.trends-history-row .trends-section {
  margin-bottom: 0;
  min-width: 0;
}

@media (max-width: 720px) {
  .trends-hero-row--split,
  .trends-history-row {
    grid-template-columns: 1fr;
  }
}

.trends-summary--risk {
  background: linear-gradient(135deg, #cf1322 0%, #a8071a 100%);
  box-shadow: 0 8px 24px rgba(207, 19, 34, 0.22);
}

.trends-summary--history {
  background: linear-gradient(135deg, #0f6e5c 0%, #095c4c 100%);
  box-shadow: 0 8px 24px rgba(15, 110, 92, 0.22);
}

.trends-summary-title {
  font-size: 20px;
  font-weight: 700;
}

.trends-summary-sub {
  font-size: 13px;
  opacity: 0.88;
  margin-top: 8px;
}

.trends-empty {
  text-align: center;
  padding: 64px 24px;
  color: #999;
  font-size: 14px;
  line-height: 1.6;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #eef0f2;
}

.trends-section {
  margin-bottom: 14px;
  position: relative;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 20px 18px 18px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #eef0f2;
}

.trends-section-1 {
  border-left: 4px solid #1677ff;
}
.trends-section-2 {
  border-left: 4px solid #722ed1;
}
.trends-section-3 {
  border-left: 4px solid #fa8c16;
}
.trends-section-4 {
  border-left: 4px solid #76de26;
}
.trends-section-5 {
  border-left: 4px solid #f30698;
}

.panel-tag {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1677ff;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-tag--forecast {
  background: #722ed1;
}

.panel-tag--alert {
  background: #fa8c16;
}

.panel-tag--record {
  background: #76de26;
  color: #1f3d0a;
}

.section-title {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 700;
  color: #222;
  padding-right: 36px;
}
.modality-summary {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 110px;
  margin-bottom: 16px;
}
.modality-summary-left {
  width: 100%;
  height: 100%;
  background: #e1f3d8;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.modality-summary-score {
  font-size: 28px;
  color: #0550eb;
  flex: 1;
  justify-content: center;
  display: flex;
  align-items: center;
  width: 120px;
  text-align: center;
  border-radius: 12px;
  font-size: 80px;
}
.modality-summary-right {
  width: 50%;
  height: 100%;
  background: #e1f3d8;
  border-radius: 12px;
  padding: 12px;
}

.risk-card {
  border-left: 4px solid #1677ff;
}

.forecast-card {
  border-left: 4px solid #722ed1;
}

.alert-card {
  border-left: 4px solid #fa8c16;
}

.record-card {
  border-left: 4px solid #76de26;
}

.modality-card {
  border-left: 4px solid #13c2c2;
  margin-bottom: 16px;
}

.panel-tag--modality {
  background: #13c2c2;
}

.behavior-card {
  border-left: 4px solid #2f54eb;
  margin-bottom: 16px;
}

.panel-tag--behavior {
  background: #2f54eb;
}

.behavior-chip {
  border-color: #e6ebff;
  background: #f5f7ff;
}

.modality-chips {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.modality-chip {
  border: 1px solid #e8f7f7;
  background: #f6fffe;
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.modality-chip--elevated {
  border-color: #ffccc7;
  background: #fff2f0;
}

.modality-chip--empty {
  border-color: #f0f0f0;
  background: #fafafa;
  opacity: 0.85;
}

.modality-chip-label {
  font-size: 12px;
  color: #666;
}

.modality-chip-score {
  font-size: 18px;
  font-weight: 700;
  color: #222;
  line-height: 1.2;
}

.modality-chip-flag {
  font-size: 12px;
  color: #13c2c2;
  font-weight: 600;
}

.modality-chip--elevated .modality-chip-flag {
  color: #cf1322;
}

.modality-chip--empty .modality-chip-flag {
  color: #999;
  font-weight: 500;
}

.modality-panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.modality-panel {
  min-width: 0;
  background: #fafbfc;
  border-radius: 12px;
  padding: 14px;
  border: 1px solid #f0f2f4;
}

.modality-forecast-summary {
  margin-bottom: 10px;
}

@media (max-width: 900px) {
  .modality-chips {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .modality-panels {
    grid-template-columns: 1fr;
  }
}

.risk-level-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.risk-badge {
  font-size: 15px;
  font-weight: 700;
  padding: 6px 14px;
  border-radius: 999px;
  line-height: 1.3;
}

.risk-low {
  background: #e8f8ee;
  color: #07c160;
}

.risk-medium {
  background: #fff8e6;
  color: #d48806;
}

.risk-high {
  background: #fff1f0;
  color: #cf1322;
}

.risk-unknown {
  background: #f5f5f5;
  color: #999;
}

.risk-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.risk-score {
  font-size: 13px;
  color: #666;
}

.risk-updated {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.risk-summary {
  margin: 0 0 12px;
  font-size: 14px;
  color: #555;
  line-height: 1.6;
}
.risk-summary2 {
  margin: 0 0 12px;
  font-size: 12px;
  color: #409eff;
  line-height: 1.6;
  margin-left: 8px;
}
.modality-summary-low {
  background: #f6ffed;
  color: #52c41a;
  margin-right: 16px;
  padding: 4px 12px;
  border-radius: 12px;
}
.modality-summary-medium {
  background: #fffbe6;
  color: #faad14;
  margin-right: 16px;
  padding: 4px 12px;
  border-radius: 12px;
}
.modality-summary-high {
  background: #fff1f0;
  color: #f5222d;
  margin-right: 16px;
  padding: 4px 12px;
  border-radius: 12px;
}

.risk-factors {
  border-top: 1px solid #f0f2f4;
  padding-top: 12px;
}

.risk-factor {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 8px;
}

.risk-factor:last-child {
  margin-bottom: 0;
}

.risk-factor-label {
  flex: 1;
  color: #333;
}

.risk-factor-value {
  color: #1677ff;
  font-weight: 600;
}

.risk-factor-source {
  font-size: 12px;
  color: #aaa;
}

.forecast-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.forecast-trend {
  display: flex;
  flex-direction: column;
}

.forecast-trend-label {
  font-size: 12px;
  color: #999;
}

.forecast-trend-value {
  font-size: 18px;
  font-weight: 700;
  color: #722ed1;
  margin-top: 2px;
}

.forecast-chart {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f2f4;
}

.forecast-day,
.trend-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.forecast-date,
.trend-date {
  width: 44px;
  flex-shrink: 0;
  font-size: 12px;
  color: #888;
}

.forecast-bar-wrap,
.trend-bar-wrap {
  flex: 1;
  height: 10px;
  background: #f0f2f5;
  border-radius: 999px;
  overflow: hidden;
  position: relative;
}

.forecast-bar,
.trend-bar {
  height: 100%;
  border-radius: 999px;
  min-width: 4px;
}

.forecast-bar-low {
  background: linear-gradient(90deg, #95de64, #52c41a);
}

.forecast-bar-medium {
  background: linear-gradient(90deg, #ffd666, #faad14);
}

.forecast-bar-high {
  background: linear-gradient(90deg, #ff7875, #f5222d);
}

.forecast-score,
.trend-value {
  width: 40px;
  text-align: right;
  flex-shrink: 0;
  font-size: 12px;
  color: #666;
  margin-left: 10px;
}

.forecast-legend {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.legend-item {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.legend-low {
  background: #f6ffed;
  color: #52c41a;
}

.legend-medium {
  background: #fffbe6;
  color: #faad14;
}

.legend-high {
  background: #fff1f0;
  color: #f5222d;
}

.risk-no-alert {
  margin: 0;
  font-size: 14px;
  color: #07c160;
  line-height: 1.6;
}

.alert-list {
  max-height: 360px;
  overflow-y: auto;
  padding-right: 2px;
}

.alert-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.alert-summary-total {
  font-size: 13px;
  color: #666;
  font-weight: 600;
}

.alert-summary-chip {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}

.alert-summary-danger {
  background: #fff1f0;
  color: #cf1322;
}

.alert-summary-warn {
  background: #fffbe6;
  color: #d48806;
}

.alert-item {
  padding: 12px 14px;
  border-radius: 10px;
  margin-bottom: 10px;
}

.alert-item-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.alert-level-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
  line-height: 1.4;
}

.alert-danger .alert-level-tag {
  background: #ffccc7;
  color: #a8071a;
}

.alert-warn .alert-level-tag {
  background: #ffe58f;
  color: #ad6800;
}

.alert-category {
  font-size: 11px;
  color: #888;
  background: rgba(0, 0, 0, 0.04);
  padding: 1px 7px;
  border-radius: 999px;
}

.alert-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.alert-metric,
.alert-source {
  font-size: 11px;
  line-height: 1.4;
  padding: 2px 8px;
  border-radius: 6px;
}

.alert-metric {
  background: rgba(22, 119, 255, 0.08);
  color: #1677ff;
  font-weight: 600;
}

.alert-source {
  background: rgba(0, 0, 0, 0.04);
  color: #999;
}

.alert-item:last-child {
  margin-bottom: 0;
}

.alert-warn {
  background: #fffbe6;
  border: 1px solid #ffe58f;
}

.alert-danger {
  background: #fff1f0;
  border: 1px solid #ffccc7;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.alert-warn .alert-title {
  color: #d48806;
}

.alert-danger .alert-title {
  color: #cf1322;
}

.alert-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.55;
}

.hint {
  margin: 0 0 8px;
  font-size: 14px;
  color: #555;
  line-height: 1.5;
}

.hint:last-child {
  margin-bottom: 0;
}

.record-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 10px;
  max-height: 360px;
  overflow-y: auto;
}

.record-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f7faf5;
  border: 1px solid #eef5e8;
  min-width: 0;
}

.record-stat-label {
  font-size: 12px;
  color: #888;
  line-height: 1.3;
}

.record-stat-value {
  font-size: 14px;
  font-weight: 700;
  color: #2f5d12;
  line-height: 1.35;
  word-break: break-all;
}

.trends-divider {
  display: flex;
  align-items: center;
  margin: 8px 0 16px;
}

.trends-divider-text {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 700;
  color: #222;
  padding-right: 36px;
  white-space: nowrap;
}

.trends-divider::before,
.trends-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: #e8e8e8;
}

.steps-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  font-size: 13px;
  color: #666;
  margin-bottom: 12px;
}

.trend-bar-ema {
  background: linear-gradient(90deg, #69b1ff, #1677ff);
}

.trend-bar-steps {
  background: linear-gradient(90deg, #95de64, #389e0d);
}

.trend-empty {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  color: #ccc;
}
</style>
