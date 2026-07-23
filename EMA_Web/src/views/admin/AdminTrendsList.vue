<template>
  <div class="page-admin-trends">
    <div class="admin-trends-top">
      <div class="admin-trends-hero">
        <div class="admin-trends-hero-main">
          <h2 class="admin-trends-title">用户趋势总览</h2>
          <div class="admin-trends-sub">
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
        <div class="admin-trends-stats">
          <div class="stat-chip stat-high">重点 {{ summary.highCount }}</div>
          <div class="stat-chip stat-medium">
            中等 {{ summary.mediumCount }}
          </div>
          <div class="stat-chip stat-low">低风险 {{ summary.lowCount }}</div>
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
        暂无普通用户趋势数据
      </div>
      <div v-else class="user-trend-list">
        <button
          v-for="(row, index) in items"
          :key="row.userId"
          type="button"
          class="user-trend-card"
          :class="[
            `level-${row.level || 'unknown'}`,
            `accent-${index % 10}`,
          ]"
          @click="openDetail(row)"
        >
          <div class="card-top">
            <div class="card-user">
              <span class="user-name">{{ row.userName }}</span>
              <span v-if="row.researchId" class="user-meta"
                >研究编号： {{ row.researchId }}</span
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
                <span style="color: #409eff">{{ row.alertCount || 0 }}</span>
                项</span
              >
              <span v-if="row.alertDangerCount"
                >重点
                <span style="color: #409eff">{{ row.alertDangerCount }}</span>
                项</span
              >
            </div>
          </div>
          <div v-if="row.criticalForced" class="critical-force-note">
            指数分档本为「{{ row.scoreBasedLevelLabel || "—" }}」；因{{
              (row.criticalReasons || []).join("、") || "关键信号"
            }}, 强制为重点关注
          </div>
          <p class="card-summary">
            {{ row.summary || "暂无风险评估摘要" }}
          </p>
          <div class="card-foot">
            <span>{{ row.updatedLabel || "暂无更新时间" }}</span>
            <span class="card-action">点击查看详情</span>
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
import { fetchAdminTrendUsers } from "../../api/adminTrends";

const props = defineProps({
  /** 默认风险等级筛选，如 high */
  defaultLevel: { type: String, default: "" },
});

const router = useRouter();
const loading = ref(true);
const error = ref("");
const items = ref([]);
const total = ref(0);
const summary = reactive({
  highCount: 0,
  mediumCount: 0,
  lowCount: 0,
});

const query = reactive({
  keyword: "",
  level: props.defaultLevel || "",
  study_status: "",
  page: 1,
  page_size: 20,
});

async function loadList() {
  loading.value = true;
  error.value = "";
  try {
    const data = await fetchAdminTrendUsers({
      keyword: query.keyword || undefined,
      level: query.level || undefined,
      study_status: query.study_status || undefined,
      page: query.page,
      page_size: query.page_size,
    });
    items.value = (data?.items || []).slice().sort((a, b) => {
      const rankDiff = (b.severityRank || 0) - (a.severityRank || 0);
      if (rankDiff !== 0) return rankDiff;
      const scoreDiff = (b.score || 0) - (a.score || 0);
      if (scoreDiff !== 0) return scoreDiff;
      return (a.userId || 0) - (b.userId || 0);
    });
    total.value = data?.total || 0;
    summary.highCount = data?.highCount || 0;
    summary.mediumCount = data?.mediumCount || 0;
    summary.lowCount = data?.lowCount || 0;
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
  query.level = props.defaultLevel || "";
  query.study_status = "";
  query.page = 1;
  loadList();
}

function openDetail(row) {
  router.push({
    name: "admin-user-trends",
    params: { userId: String(row.userId) },
  });
}

onMounted(loadList);
</script>

<style scoped>
.page-admin-trends {
  width: 100%;
}

.admin-trends-top {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}

.admin-trends-hero {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 16px;
  min-height: 100%;
  padding: 22px 24px;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%);
  box-shadow: 0 8px 24px rgba(22, 119, 255, 0.22);
}

.admin-trends-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
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

.admin-trends-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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

.page-card {
  border-radius: 16px;
}

.filter-card {
  display: flex;
  flex-direction: column;
}

.filter-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px 20px;
}

.filter-form {
  width: 100%;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 8px;
}

.filter-actions :deep(.el-form-item__content) {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .admin-trends-top {
    grid-template-columns: 1fr;
  }
}

.empty-tip {
  padding: 48px 16px;
  text-align: center;
  color: #999;
}

.user-trend-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.user-trend-card {
  text-align: left;
  border: 1px solid #eef0f2;
  border-radius: 14px;
  background: #fff;
  padding: 16px;
  cursor: pointer;
  border-left: 4px solid #1677ff;
  transition:
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.user-trend-card:hover {
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}

.user-trend-card.accent-0 {
  border-left-color: #1677ff;
}
.user-trend-card.accent-1 {
  border-left-color: #fa8c16;
}
.user-trend-card.accent-2 {
  border-left-color: #722ed1;
}
.user-trend-card.accent-3 {
  border-left-color: #13c2c2;
}
.user-trend-card.accent-4 {
  border-left-color: #eb2f96;
}
.user-trend-card.accent-5 {
  border-left-color: #52c41a;
}
.user-trend-card.accent-6 {
  border-left-color: #2f54eb;
}
.user-trend-card.accent-7 {
  border-left-color: #fa541c;
}
.user-trend-card.accent-8 {
  border-left-color: #a0d911;
}
.user-trend-card.accent-9 {
  border-left-color: #f5222d;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.user-name {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #222;
}

.user-meta {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  color: #1677ff;
}

.risk-badge {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
}

.card-badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.critical-force-tag {
  font-size: 11px;
  font-weight: 700;
  color: #a8071a;
  background: #ffccc7;
  padding: 2px 8px;
  border-radius: 999px;
}

.critical-force-note {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff1f0;
  border: 1px solid #ffccc7;
  font-size: 12px;
  color: #a8071a;
  line-height: 1.5;
}

.risk-high {
  background: #fff1f0;
  color: #cf1322;
}

.risk-medium {
  background: #fffbe6;
  color: #d48806;
}

.risk-low {
  background: #f6ffed;
  color: #52c41a;
}

.risk-unknown {
  background: #f5f5f5;
  color: #999;
}

.card-mid {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
}

.score-label {
  display: block;
  font-size: 12px;
  color: #888;
}

.score-value {
  font-size: 28px;
  font-weight: 700;
  color: #1677ff;
  line-height: 1.1;
}

.alert-block {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.card-summary {
  margin: 12px 0 0;
  font-size: 13px;
  color: #faad14;
  line-height: 1.55;
  min-height: 40px;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f0f2f4;
  font-size: 12px;
  color: #999;
}

.card-action {
  color: #1677ff;
  font-weight: 600;
  font-size: 16px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .admin-trends-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .user-trend-list {
    grid-template-columns: 1fr;
  }
}
</style>
