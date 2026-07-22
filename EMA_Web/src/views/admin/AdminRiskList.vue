<template>
  <div class="page-admin-risk">
    <div class="admin-risk-top">
      <div class="admin-risk-hero">
        <div class="admin-risk-hero-left">
          <div class="admin-risk-hero-main">
            <h2 class="admin-risk-title">用户风险预警</h2>
            <p class="admin-risk-sub">展示全部普通用户的风险预警概况。</p>
            <p class="admin-risk-sub">按风险等级严重程度从高到低排序。</p>
            <p class="admin-risk-sub">点击用户可查看详细预警。</p>
          </div>
          <div class="admin-risk-stats">
            <div class="stat-chip stat-high">重点 {{ summary.highCount }}</div>
            <div class="stat-chip stat-medium">
              中等 {{ summary.mediumCount }}
            </div>
            <div class="stat-chip stat-low">低风险 {{ summary.lowCount }}</div>
            <div class="stat-chip stat-alert">
              有预警 {{ summary.alertUserCount }}
            </div>
          </div>
        </div>
        <div class="admin-risk-hero-right">
          <h2 class="admin-risk-title">风险指数说明</h2>
          <div class="admin-risk-sub">
            风险指数范围是 0–15（与现有风险评估的风险指数一致）
          </div>
          <div class="admin-trends-sub" style="margin: 8px 0">
            <span class="modality-summary-low">低风险：0–4</span>
            <span class="modality-summary-medium">中等关注：5–9</span>
            <span class="modality-summary-high">需重点关注：10–15</span>
            <div class="modality-summary-critical">
              另：基线自伤阳性或当日消极想法为「是」时，将强制判定为需重点关注。
            </div>
            <div class="modality-summary-critical">
              并标注为<span style="color: #fff">'关键强制'</span
              >和原因（基线自伤筛查阳性/当日问卷报告明显消极想法）
            </div>
          </div>
        </div>
      </div>

      <el-card shadow="never" class="page-card filter-card">
        <el-form
          :inline="false"
          :model="query"
          class="filter-form"
          label-width="72px"
          @submit.prevent
        >
          <el-form-item label="关键词">
            <el-input
              v-model="query.keyword"
              clearable
              placeholder="用户名 / 研究编号"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item label="风险等级">
            <el-select
              v-model="query.level"
              clearable
              placeholder="全部"
              style="width: 100%"
            >
              <el-option label="需重点关注" value="high" />
              <el-option label="中等关注" value="medium" />
              <el-option label="低风险" value="low" />
              <el-option label="待评估" value="unknown" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.study_status"
              clearable
              placeholder="全部"
              style="width: 100%"
            >
              <el-option label="激活" value="active" />
              <el-option label="撤回同意" value="consent_revoked" />
              <el-option label="退出研究" value="exited" />
            </el-select>
          </el-form-item>
          <el-form-item class="filter-actions" label-width="0">
            <el-button type="primary" @click="onSearch">查询</el-button>
            <el-button @click="onReset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <el-card shadow="never" class="page-card list-card">
      <el-skeleton v-if="loading" :rows="6" animated />
      <el-alert
        v-else-if="error"
        type="error"
        :title="error"
        show-icon
        :closable="false"
      />
      <div v-else-if="!items.length" class="empty-tip">
        暂无普通用户风险预警数据
      </div>
      <div v-else class="user-risk-list">
        <button
          v-for="row in items"
          :key="row.userId"
          type="button"
          class="user-risk-card"
          :class="`level-${row.level || 'unknown'}`"
          @click="openDetail(row)"
        >
          <div class="card-top">
            <div class="card-user">
              <span class="user-name">{{ row.userName }}</span>
              <span v-if="row.researchId" class="user-meta"
                >研究编号：{{ row.researchId }}</span
              >
            </div>
            <div class="card-badges">
              <span class="risk-badge" :class="row.levelClass">{{
                row.levelLabel || "待评估"
              }}</span>
              <span v-if="row.criticalForced" class="critical-force-tag"
                >关键强制</span
              >
            </div>
          </div>
          <div class="card-mid">
            <div class="score-block">
              <span class="score-label">风险指数</span>
              <span
                class="score-value"
                :style="{
                  color:
                    row.score >= 10
                      ? '#f5222d'
                      : row.score >= 5
                        ? '#faad14'
                        : '#52c41a',
                }"
                >{{ row.score ?? "--" }}</span
              >
            </div>
            <div class="alert-block">
              <span
                >预警
                <em>{{ row.alertCount || 0 }}</em>
                项</span
              >
              <span v-if="row.alertDangerCount"
                >重点
                <em>{{ row.alertDangerCount }}</em>
                项</span
              >
              <span v-if="row.alertWarnCount"
                >留意
                <em>{{ row.alertWarnCount }}</em>
                项</span
              >
              <span v-if="row.alertInfoCount"
                >提示
                <em>{{ row.alertInfoCount }}</em>
                项</span
              >
              <span v-if="row.forecastAlertCount"
                >30天
                <em>{{ row.forecastAlertCount }}</em>
                项</span
              >
              <span v-if="row.emaFeatureAlertCount"
                >五特性
                <em>{{ row.emaFeatureAlertCount }}</em>
                项</span
              >
              <span v-if="row.behaviorAnalysisAlertCount"
                >行为
                <em>{{ row.behaviorAnalysisAlertCount }}</em>
                项</span
              >
            </div>
          </div>
          <div v-if="row.forecast30HighDays || row.forecastAlertCount" class="forecast30-note">
            未来30天：重点 {{ row.forecast30HighDays || 0 }} 天
            <template v-if="row.forecast30PeakLabel"
              > · 峰值「{{ row.forecast30PeakLabel }}」</template
            >
          </div>
          <div v-if="row.criticalForced" class="critical-force-note">
            指数分档本为「{{ row.scoreBasedLevelLabel || "—" }}」；因{{
              (row.criticalReasons || []).join("、") || "关键信号"
            }}强制为重点关注
          </div>
          <ul
            v-if="row.topForecastAlerts?.length || row.topAlerts?.length"
            class="top-alerts"
          >
            <li
              v-for="alert in (row.topForecastAlerts?.length
                ? row.topForecastAlerts
                : row.topAlerts
              ).slice(0, 3)"
              :key="alert.id"
              class="top-alert"
              :class="`alert-${alert.level || 'warn'}`"
            >
              <div class="top-alert-head">
                <span class="top-alert-tag">{{
                  alert.levelLabel || "预警"
                }}</span>
                <span v-if="alert.category" class="top-alert-cat">{{
                  alert.category
                }}</span>
              </div>
              <span class="top-alert-title">{{ alert.title }}</span>
              <span v-if="alert.desc" class="top-alert-desc">{{
                alert.desc
              }}</span>
            </li>
          </ul>
          <p v-else class="card-summary">
            {{ row.summary || "暂无风险预警摘要" }}
          </p>
          <div class="card-foot">
            <span>{{ row.updatedLabel || "暂无更新时间" }}</span>
            <span class="card-action">点击查看预警详情</span>
          </div>
        </button>
      </div>

      <div v-if="total > query.page_size" class="pager">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadList"
          @current-change="loadList"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchAdminRiskUsers } from "../../api/adminRisk";

const router = useRouter();
const loading = ref(true);
const error = ref("");
const items = ref([]);
const total = ref(0);
const summary = reactive({
  highCount: 0,
  mediumCount: 0,
  lowCount: 0,
  alertUserCount: 0,
});

const query = reactive({
  keyword: "",
  level: "",
  study_status: "",
  page: 1,
  page_size: 20,
});

async function loadList() {
  loading.value = true;
  error.value = "";
  try {
    const data = await fetchAdminRiskUsers({
      keyword: query.keyword || undefined,
      level: query.level || undefined,
      study_status: query.study_status || undefined,
      page: query.page,
      page_size: query.page_size,
    });
    items.value = data?.items || [];
    total.value = data?.total || 0;
    summary.highCount = data?.highCount || 0;
    summary.mediumCount = data?.mediumCount || 0;
    summary.lowCount = data?.lowCount || 0;
    summary.alertUserCount = data?.alertUserCount || 0;
  } catch (e) {
    error.value = e.message || String(e);
    items.value = [];
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  query.page = 1;
  loadList();
}

function onReset() {
  query.keyword = "";
  query.level = "";
  query.study_status = "";
  query.page = 1;
  loadList();
}

function openDetail(row) {
  router.push({
    name: "admin-user-risk",
    params: { userId: String(row.userId) },
  });
}

onMounted(loadList);
</script>

<style scoped>
.page-admin-risk {
  width: 100%;
}

.admin-risk-top {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}

.admin-risk-hero {
  display: flex;
  flex-direction: row;
  gap: 16px;
  min-height: 100%;
  padding: 22px 24px;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, #1677ff 0%, #078da8 100%);
  box-shadow: 0 8px 24px rgba(207, 19, 34, 0.22);
}
.admin-risk-hero-left {
  width: 45%;
  height: 100%;
}
.admin-risk-hero-right {
  flex: 1;
  height: 100%;
}
.admin-trends-sub {
  font-size: 13px;
  opacity: 0.9;
  line-height: 1.5;
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
.modality-summary-critical {
  margin-top: 8px;
  font-size: 12px;
  color: #b3e19d;
}
.admin-risk-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}

.admin-risk-sub {
  margin: 8px 0 0;
  font-size: 13px;
  opacity: 0.92;
  line-height: 1.5;
}

.admin-risk-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.stat-chip {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.16);
}
.stat-high {
  background: #fff1f0;
  color: #f5222d;
}
.stat-medium {
  background: #fffbe6;
  color: #faad14;
}
.stat-low {
  background: #f6ffed;
  color: #52c41a;
}
.stat-alert {
  background: #f6ffed;
  color: #c41a70;
}

.page-card {
  border-radius: 16px;
}

.filter-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 18px 20px 8px;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.filter-actions :deep(.el-form-item__content) {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.empty-tip {
  padding: 48px 16px;
  text-align: center;
  color: #999;
}

.user-risk-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.user-risk-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding: 16px;
  text-align: left;
  border: 1px solid #eef0f2;
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.user-risk-card:hover {
  border-color: #ffa39e;
  box-shadow: 0 8px 20px rgba(207, 19, 34, 0.1);
  transform: translateY(-1px);
}

.user-risk-card.level-high {
  border-left: 4px solid #f5222d;
}

.user-risk-card.level-medium {
  border-left: 4px solid #faad14;
}

.user-risk-card.level-low {
  border-left: 4px solid #52c41a;
}

.user-risk-card.level-unknown {
  border-left: 4px solid #bfbfbf;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.card-user {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-name {
  font-size: 16px;
  font-weight: 700;
  color: #222;
}

.user-meta {
  margin-top: 2px;
  font-size: 12px;
  color: #8c8c8c;
}

.card-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.risk-badge.risk-high,
:deep(.risk-high) {
  color: #cf1322;
  background: #fff1f0;
}

.risk-badge.risk-medium,
:deep(.risk-medium) {
  color: #d48806;
  background: #fffbe6;
}

.risk-badge.risk-low,
:deep(.risk-low) {
  color: #389e0d;
  background: #f6ffed;
}

.risk-badge.risk-unknown,
:deep(.risk-unknown) {
  color: #8c8c8c;
  background: #f5f5f5;
}

.critical-force-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: #cf1322;
}

.card-mid {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.score-block {
  display: flex;
  flex-direction: column;
}

.score-label {
  font-size: 12px;
  color: #8c8c8c;
}

.score-value {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.1;
}

.alert-block {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 13px;
  color: #595959;
}

.alert-block em {
  font-style: normal;
  font-weight: 700;
  color: #1677ff;
}

.critical-force-note {
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #a8071a;
  background: #fff1f0;
}

.forecast30-note {
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  color: #c41d7f;
  background: #fff0f6;
}

.top-alerts {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
  max-height: 150px;
}

.top-alert {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fafafa;
}

.top-alert.alert-danger {
  background: #fff1f0;
}

.top-alert.alert-warn {
  background: #fffbe6;
}

.top-alert.alert-info {
  background: #f0f5ff;
}

.top-alert-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.top-alert-tag {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  color: #8c8c8c;
}

.top-alert-cat {
  font-size: 11px;
  color: #8c8c8c;
}

.alert-danger .top-alert-tag {
  color: #cf1322;
}

.alert-warn .top-alert-tag {
  color: #d48806;
}

.alert-info .top-alert-tag {
  color: #2f54eb;
}

.top-alert-title {
  font-size: 13px;
  font-weight: 600;
  color: #262626;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-alert-desc {
  font-size: 12px;
  line-height: 1.4;
  color: #8c8c8c;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-summary {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #595959;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
  padding-top: 4px;
  font-size: 12px;
  color: #8c8c8c;
}

.card-action {
  color: #cf1322;
  font-weight: 600;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .admin-risk-top,
  .user-risk-list {
    grid-template-columns: 1fr;
  }
}
</style>
