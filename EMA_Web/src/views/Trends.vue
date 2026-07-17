<template>
  <div class="page-trends">
    <div class="trends-summary" :class="summaryClass">
      <div class="trends-summary-title">{{ summaryTitle }}</div>
      <div class="trends-summary-sub">{{ summarySub }}</div>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />
    <el-alert v-else-if="error" type="error" :title="error" show-icon :closable="false" />

    <template v-else>
      <template v-if="showRisk">
        <div v-if="!risk.hasAssessment" class="trends-empty">
          完成基线测评或 EMA 打卡后，将展示风险评估与预测信息
        </div>

        <template v-if="risk.hasAssessment">
          <section class="trends-section card risk-card">
            <span class="panel-tag">01</span>
            <h3 class="section-title">当前风险评估</h3>
            <div class="risk-level-row">
              <span class="risk-badge" :class="current.levelClass">{{ current.levelLabel }}</span>
              <div class="risk-meta">
                <span class="risk-score">风险指数 {{ current.score ?? '--' }}</span>
                <span class="risk-updated">{{ current.updatedLabel || '' }}</span>
              </div>
            </div>
            <p class="risk-summary">{{ current.summary || '暂无摘要' }}</p>
            <div v-if="current.factors?.length" class="risk-factors">
              <div v-for="item in current.factors" :key="item.label" class="risk-factor">
                <span class="risk-factor-label">{{ item.label }}</span>
                <span class="risk-factor-value">{{ item.value }}</span>
                <span class="risk-factor-source">{{ item.source }}</span>
              </div>
            </div>
          </section>

          <section class="trends-section card forecast-card">
            <span class="panel-tag panel-tag--forecast">02</span>
            <h3 class="section-title">未来 7 天风险预测</h3>
            <div class="forecast-head">
              <div class="forecast-trend">
                <span class="forecast-trend-label">趋势走向</span>
                <span class="forecast-trend-value">{{ forecast.trendLabel || '—' }}</span>
              </div>
              <span class="risk-badge" :class="forecast.peakLevelClass">
                {{ forecast.peakLevelLabel || '待评估' }}
              </span>
            </div>
            <p class="risk-summary">{{ forecast.summary || '' }}</p>
            <div v-if="forecast.days?.length" class="forecast-chart">
              <div v-for="day in forecast.days" :key="day.dayIndex" class="forecast-day">
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
            <p v-if="!risk.alertCount" class="risk-no-alert">暂无异常信号，状态整体平稳。</p>
            <div
              v-for="item in risk.alerts || []"
              :key="item.id"
              class="alert-item"
              :class="`alert-${item.level}`"
            >
              <div class="alert-title">{{ item.title }}</div>
              <div class="alert-desc">{{ item.desc }}</div>
            </div>
          </section>

          <section class="trends-section card record-card">
            <span class="panel-tag panel-tag--record">04</span>
            <h3 class="section-title">打卡概况</h3>
            <p v-if="!hasData" class="risk-no-alert">暂无打卡概况数据。</p>
            <template v-else>
              <p class="hint">连续缺测：{{ stats.missedDays ?? 0 }} 天</p>
              <p class="hint">平均日记字数：{{ stats.avgDiaryWords ?? 0 }}</p>
              <p class="hint">平均语音时长：{{ stats.avgVoiceSec ?? 0 }} 秒</p>
            </template>
          </section>
        </template>
      </template>

      <div v-if="showRisk && showHistory && hasData && risk.hasAssessment" class="trends-divider">
        <span class="trends-divider-text">历史数据趋势</span>
      </div>

      <template v-if="showHistory">
        <div v-if="!hasData && !showRisk" class="trends-empty">
          完成 EMA 打卡后，将展示历史趋势数据
        </div>

        <section v-if="hasData && metrics.length" class="trends-section card">
          <h3 class="section-title">EMA 指标（0–10）</h3>
          <div v-for="metric in metrics" :key="metric.id" class="metric-block">
            <div class="metric-title">{{ metric.label }}</div>
            <div v-for="point in metric.points" :key="`${metric.id}-${point.dateLabel}`" class="trend-row">
              <span class="trend-date">{{ point.dateLabel }}</span>
              <div class="trend-bar-wrap">
                <div
                  v-if="point.hasData"
                  class="trend-bar trend-bar-ema"
                  :style="{ width: `${point.barWidth || 0}%` }"
                />
                <span v-else class="trend-empty">—</span>
              </div>
              <span class="trend-value">{{ point.hasData ? point.value : '' }}</span>
            </div>
          </div>
        </section>

        <section v-if="hasData && stepsTrend.length" class="trends-section card">
          <h3 class="section-title">运动步数</h3>
          <div class="steps-meta">
            <span>今日 {{ stepsAnalytics.today || 0 }} 步</span>
            <span>7 日均 {{ stepsAnalytics.avg7 || 0 }} 步</span>
            <span v-if="stepsAnalytics.baseline">基线 {{ stepsAnalytics.baseline }} 步</span>
          </div>
          <div v-for="item in stepsTrend" :key="item.dateLabel" class="trend-row">
            <span class="trend-date">{{ item.dateLabel }}</span>
            <div class="trend-bar-wrap">
              <div
                v-if="item.hasData"
                class="trend-bar trend-bar-steps"
                :style="{ width: `${item.barWidth || 0}%` }"
              />
              <span v-else class="trend-empty">—</span>
            </div>
            <span class="trend-value">{{ item.hasData ? item.steps : '' }}</span>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ensureLogin } from '../api/auth'
import { fetchTrendsOverview } from '../api/ema'
import { trackEvent } from '../utils/tracker'

const props = defineProps({
  /** all | risk | history */
  mode: { type: String, default: 'all' },
})

const loading = ref(true)
const error = ref('')
const hasData = ref(false)
const risk = ref({})
const metrics = ref([])
const stepsTrend = ref([])
const stepsAnalytics = ref({})
const stats = ref({})

const current = computed(() => risk.value?.current || {})
const forecast = computed(() => risk.value?.forecast || {})
const showRisk = computed(() => props.mode === 'all' || props.mode === 'risk')
const showHistory = computed(() => props.mode === 'all' || props.mode === 'history')

const summaryTitle = computed(() => {
  if (props.mode === 'risk') return '风险分析'
  if (props.mode === 'history') return '趋势分析'
  return '心理健康趋势与风险'
})
const summarySub = computed(() => {
  if (props.mode === 'risk') return '当前评估 · 未来预测 · 异常预警'
  if (props.mode === 'history') return 'EMA 指标 · 运动步数'
  return '当前评估 · 未来预测 · 异常预警'
})
const summaryClass = computed(() => ({
  'trends-summary--risk': props.mode === 'risk',
  'trends-summary--history': props.mode === 'history',
}))

onMounted(async () => {
  loading.value = true
  try {
    await ensureLogin()
    trackEvent(props.mode === 'risk' ? 'risk' : 'trends', 'view')
    const data = await fetchTrendsOverview(7)
    hasData.value = !!(data && (data.hasData || data.has_data))
    risk.value = data?.risk || {}
    metrics.value = data?.metrics || []
    stepsTrend.value = data?.stepsTrend || data?.steps_trend || []
    stepsAnalytics.value = data?.stepsAnalytics || data?.steps_analytics || {}
    stats.value = data?.stats || {}
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-trends {
  max-width: 720px;
  margin: 0 auto;
  padding-bottom: 24px;
}

.trends-summary {
  background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%);
  border-radius: 16px;
  padding: 28px 24px;
  margin-bottom: 16px;
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 8px 24px rgba(22, 119, 255, 0.22);
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

.alert-item {
  padding: 12px 14px;
  border-radius: 10px;
  margin-bottom: 10px;
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

.trends-divider {
  display: flex;
  align-items: center;
  margin: 8px 0 16px;
}

.trends-divider-text {
  font-size: 12px;
  color: #999;
  padding: 0 12px;
  white-space: nowrap;
}

.trends-divider::before,
.trends-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e8e8e8;
}

.metric-block + .metric-block {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #f0f2f4;
}

.metric-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
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
