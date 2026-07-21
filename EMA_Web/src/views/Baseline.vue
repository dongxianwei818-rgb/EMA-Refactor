<template>
  <div class="baseline-shell">
    <OnboardingHeader title="基线测评" />
    <div class="baseline-page">
      <el-alert type="warning" show-icon :closable="false" class="hint-banner">
        基线测评仅采集一次。回答越详细，预测越准确。
      </el-alert>

      <div class="baseline-grid">
        <div
          v-for="section in sections"
          :key="section.id"
          class="section-block baseline-cell"
        >
          <h2 class="section-title">{{ section.title }}</h2>
          <p v-if="section.hint" class="section-hint">{{ section.hint }}</p>

          <el-card v-if="section.fields" shadow="never" class="form-card">
            <el-form label-position="top">
              <el-form-item v-for="f in section.fields" :key="f.id">
                <template #label>
                  {{ f.label }}
                  <span v-if="f.required" class="required">*</span>
                </template>
                <el-input
                  v-if="f.type === 'input'"
                  v-model="form[f.id]"
                  :type="f.inputType || 'text'"
                  placeholder="请输入"
                />
                <el-radio-group
                  v-else-if="f.type === 'radio'"
                  v-model="form[f.id]"
                  class="radio-group"
                >
                  <el-radio v-for="opt in f.options" :key="opt" :value="opt">{{
                    opt
                  }}</el-radio>
                </el-radio-group>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card v-if="section.items" shadow="never" class="form-card">
            <div v-for="q in section.items" :key="q.id" class="question-item">
              <div class="question-label">
                {{ q.label }}
                <span v-if="!q.optional" class="required">*</span>
                <span v-else class="optional">（选填）</span>
              </div>
              <el-radio-group v-model="form[q.id]" class="radio-group">
                <el-radio v-for="opt in q.options" :key="opt" :value="opt">
                  {{ opt }}
                </el-radio>
              </el-radio-group>
            </div>
          </el-card>
        </div>
      </div>

      <div class="baseline-footer">
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="submitting"
          @click="onSubmit"
        >
          完成基线（仅采集一次）
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import OnboardingHeader from "../components/OnboardingHeader.vue";
import { BASELINE_SECTIONS } from "../constants/ema";
import { submitBaselineLog } from "../api/ema";
import { ensureLogin } from "../api/auth";
import {
  bindResearchFromBaseline,
  hasBaseline,
  isResearchBound,
  saveBaseline,
} from "../utils/ema";
import { markOnboardingSynced } from "../utils/onboardingGate";
import { endTaskTimer, startTaskTimer, trackEvent } from "../utils/tracker";

const router = useRouter();
const sections = BASELINE_SECTIONS;
const form = reactive({});
const submitting = ref(false);

onMounted(async () => {
  try {
    await ensureLogin();
  } catch (e) {
    router.replace("/login");
    return;
  }
  if (isResearchBound() || hasBaseline()) {
    ElMessage.info("基线测评已完成");
    router.replace("/home");
    return;
  }
  trackEvent("baseline", "view", {}, "/baseline");
  startTaskTimer("baseline");
});

function validate() {
  const req = [
    "researchId",
    "age",
    "gender",
    "grade",
    "major",
    "onlyChild",
    "housing",
  ];
  for (const id of req) {
    if (!form[id]) {
      ElMessage.warning("请完成基本信息");
      return false;
    }
  }
  const items = [
    "course_pressure",
    "exam_pressure",
    "gpa_pressure",
    "job_pressure",
    "sleep_habit",
    "exercise_freq",
    "social_freq",
    "phq9_1",
    "phq9_2",
    "gad7_1",
    "gad7_2",
  ];
  for (const id of items) {
    if (!form[id]) {
      ElMessage.warning("请完成学业、生活与量表题");
      return false;
    }
  }
  return true;
}

async function onSubmit() {
  if (!validate() || submitting.value) return;
  submitting.value = true;
  const at = Date.now();
  saveBaseline({ ...form, at });
  endTaskTimer("baseline");
  trackEvent("baseline", "submit", {}, "/baseline");
  try {
    const data = await submitBaselineLog(form, at);
    bindResearchFromBaseline(data, form);
    markOnboardingSynced();
    ElMessage.success("保存成功");
    router.replace("/home");
  } catch (e) {
    ElMessage.error(e.message || "提交失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.baseline-shell {
  height: 100vh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #eef3f1;
}

.baseline-page {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  width: 100%;
  margin: 0 auto;
  padding: 16px;
  overflow: hidden;
}

.hint-banner {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.baseline-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  flex: 1;
  min-height: 0;
  align-content: flex-start;
  align-items: stretch;
  overflow-y: auto;
  padding-bottom: 8px;
}

.baseline-cell {
  flex: 0 1 calc(50% - 8px);
  width: calc(50% - 8px);
  max-width: calc(50% - 8px);
  min-width: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

@media (max-width: 720px) {
  .baseline-cell {
    flex: 0 1 100%;
    width: 100%;
    max-width: 100%;
  }
}

.section-title {
  margin: 0 0 8px;
  font-size: 18px;
  color: #0f6e5c;
}

.section-hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 12px;
}

.form-card {
  flex: 1;
  margin-bottom: 0;
  border-radius: 12px;
}

.question-item {
  margin-bottom: 20px;
}

.question-item:last-child {
  margin-bottom: 0;
}

.question-label {
  font-weight: 500;
  margin-bottom: 8px;
}

.required {
  color: #f56c6c;
}

.optional {
  color: #909399;
  font-size: 12px;
}

.radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.baseline-footer {
  flex-shrink: 0;
  padding-top: 12px;
  justify-content: center;
  display: flex;
}

.submit-btn {
  width: 300px;
}
</style>
