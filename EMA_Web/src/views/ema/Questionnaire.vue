<template>
  <div class="ema-task-page">
    <el-card shadow="never">
      <h2>每日 EMA 问卷</h2>
      <p class="hint">8 项 · 0–10 分 · 约 30–60 秒</p>

      <div v-for="q in questions" :key="q.id" class="question-block">
        <div class="q-label">{{ q.label }}</div>
        <el-slider
          v-if="q.type === 'scale10'"
          v-model="answers[q.id]"
          :min="0"
          :max="10"
          :step="1"
          show-stops
        />
        <el-radio-group
          v-else-if="q.type === 'ternary'"
          v-model="answers[q.id]"
        >
          <el-radio v-for="opt in q.options" :key="opt" :value="opt">{{
            opt
          }}</el-radio>
        </el-radio-group>
      </div>

      <el-button
        type="primary"
        class="submit-btn"
        :loading="submitting"
        @click="onSubmit"
      >
        提交问卷
      </el-button>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { EMA_QUESTIONS } from "../../constants/ema";
import { submitQuestionnaireLog } from "../../api/ema";
import {
  ensureCheckinSession,
  getCurrentSessionId,
  getTodayKey,
  markTaskDone,
  saveSubmission,
} from "../../utils/ema";
import { runStepSubmit } from "../../utils/emaFlow";
import { endTaskTimer, startTaskTimer, trackEvent } from "../../utils/tracker";

const router = useRouter();
const questions = EMA_QUESTIONS;
const answers = reactive({});
const submitting = ref(false);
const startAt = ref(0);

onMounted(() => {
  ensureCheckinSession();
  EMA_QUESTIONS.forEach((q) => {
    answers[q.id] = q.type === "scale10" ? 5 : "";
  });
  startAt.value = Date.now();
  trackEvent("questionnaire", "view", {}, "/ema/questionnaire");
  startTaskTimer("questionnaire");
});

async function onSubmit() {
  if (submitting.value) return;
  if (!answers.negative) {
    ElMessage.warning("请回答消极想法条目");
    return;
  }
  submitting.value = true;
  const sec = Math.round((Date.now() - startAt.value) / 1000);
  const at = Date.now();
  markTaskDone("questionnaire");
  saveSubmission("questionnaire", {
    answers: { ...answers },
    durationSec: sec,
  });
  endTaskTimer("questionnaire");
  trackEvent("questionnaire", "submit", {
    durationSec: sec,
    sessionId: getCurrentSessionId(),
  });
  try {
    await runStepSubmit({
      router,
      submit: () =>
        submitQuestionnaireLog(
          { ...answers },
          at,
          getCurrentSessionId(),
          getTodayKey(),
          sec,
        ),
      successToast: "已提交",
    });
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.ema-task-page {
  max-width: 640px;
  margin: 0 auto;
}

.hint {
  color: #909399;
  margin-bottom: 20px;
}

.question-block {
  margin-bottom: 24px;
}

.q-label {
  font-weight: 500;
  margin-bottom: 10px;
}

.submit-btn {
  width: 100%;
  margin-top: 12px;
}
</style>
