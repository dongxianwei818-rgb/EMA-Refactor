<template>
  <div class="ema-task-page">
    <el-card shadow="never">
      <h2>语音任务</h2>
      <p class="prompt">{{ prompt }}</p>
      <p class="hint">建议录制 {{ minSec }}–{{ maxSec }} 秒</p>

      <el-alert
        v-if="intervalHint"
        type="warning"
        :title="intervalHint"
        show-icon
        :closable="false"
        class="interval-alert"
      />

      <div class="record-panel">
        <!-- <el-tag :type="phaseTagType" size="large">{{ recordText }}</el-tag> -->
        <div class="btn-row">
          <el-button
            v-if="phase === 'idle' || phase === 'recording'"
            :type="phase === 'recording' ? 'danger' : 'primary'"
            @click="toggleRecord"
          >
            {{ phase === "recording" ? "停止录音" : "开始录音" }}
          </el-button>
          <el-button v-if="phase !== 'submitting'" @click="onSkip"
            >跳过本次</el-button
          >
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  RANDOM_QUESTION,
  VOICE_MAX_SEC,
  VOICE_MIN_SEC,
  VOICE_PROMPTS,
} from "../../constants/ema";
import { submitVoiceSkipLog, uploadVoiceLog } from "../../api/ema";
import {
  ensureCheckinSession,
  getCurrentSessionId,
  getRecordingIntervalStatus,
  getTodayKey,
  markTaskDone,
  markVoiceSkipped,
  saveSubmission,
} from "../../utils/ema";
import { runStepSubmit } from "../../utils/emaFlow";
import { endTaskTimer, startTaskTimer, trackEvent } from "../../utils/tracker";

const router = useRouter();
const prompt = `${RANDOM_QUESTION}\n${VOICE_PROMPTS.join("\n")}`;
const minSec = VOICE_MIN_SEC;
const maxSec = VOICE_MAX_SEC;
const phase = ref("idle");
const recordText = ref("开始录音");
const duration = ref(0);
const submitting = ref(false);
const intervalHint = ref("");

let mediaRecorder = null;
let audioChunks = [];
let tickTimer = null;
let recordStart = 0;

const phaseTagType = computed(() => {
  if (phase.value === "recording") return "danger";
  if (phase.value === "submitting") return "warning";
  return "info";
});

onMounted(async () => {
  ensureCheckinSession();
  trackEvent("voice", "view", {}, "/ema/voice");
  startTaskTimer("voice");
  const status = getRecordingIntervalStatus("voice");
  if (!status.due) {
    intervalHint.value = `距上次语音录制未满 ${status.intervalDays} 天（还需约 ${status.daysRemaining} 天）`;
    try {
      await ElMessageBox.confirm(
        intervalHint.value + "。可直接进行下一步，或重新录制。",
        "录音间隔提醒",
        { confirmButtonText: "直接进行下一步", cancelButtonText: "重新录制" },
      );
      await skipToNext();
    } catch {
      trackEvent("voice", "rer_record_interval");
    }
  }
});

onBeforeUnmount(() => {
  clearTimers();
  if (mediaRecorder?.state === "recording") {
    try {
      mediaRecorder.stop();
    } catch {
      /* ignore */
    }
  }
});

function clearTimers() {
  if (tickTimer) {
    clearInterval(tickTimer);
    tickTimer = null;
  }
}

async function toggleRecord() {
  if (phase.value === "recording") {
    stopRecord();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    mediaRecorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      finishRecord();
    };
    recordStart = Date.now();
    phase.value = "recording";
    recordText.value = "录音中…";
    trackEvent("voice", "record_start");
    mediaRecorder.start();
    tickTimer = setInterval(() => {
      const sec = Math.floor((Date.now() - recordStart) / 1000);
      duration.value = sec;
      recordText.value = `${sec} 秒`;
      if (sec >= maxSec) stopRecord();
    }, 400);
  } catch {
    ElMessage.error("无法访问麦克风，请检查浏览器权限");
  }
}

function stopRecord() {
  clearTimers();
  if (mediaRecorder?.state === "recording") {
    phase.value = "processing";
    recordText.value = "处理中…";
    mediaRecorder.stop();
  }
}

function finishRecord() {
  const sec = duration.value || Math.floor((Date.now() - recordStart) / 1000);
  if (sec < minSec) {
    phase.value = "idle";
    recordText.value = "开始录音";
    ElMessage.warning(`至少录制 ${minSec} 秒`);
    return;
  }
  const blob = new Blob(audioChunks, { type: "audio/webm" });
  const file = new File([blob], `voice_${Date.now()}.webm`, {
    type: blob.type,
  });
  submitAndNext(file, sec);
}

async function submitAndNext(file, sec) {
  if (submitting.value) return;
  submitting.value = true;
  phase.value = "submitting";
  recordText.value = "提交中…";
  const at = Date.now();
  markTaskDone("voice");
  saveSubmission("voice", { duration: sec, prompt });
  endTaskTimer("voice");
  trackEvent("voice", "submit", { duration: sec });
  try {
    await runStepSubmit({
      router,
      submit: () =>
        uploadVoiceLog(file, sec, at, getCurrentSessionId(), getTodayKey()),
      successToast: "已提交",
      onError: (err) => {
        phase.value = "idle";
        recordText.value = "开始录音";
        ElMessage.error(err.message || "提交失败");
      },
    });
  } finally {
    submitting.value = false;
  }
}

async function skipToNext() {
  if (submitting.value) return;
  submitting.value = true;
  const at = Date.now();
  markTaskDone("voice");
  saveSubmission("voice", { skip: true, reason: "interval" }, { at });
  endTaskTimer("voice");
  trackEvent("voice", "skip_interval");
  try {
    await runStepSubmit({
      router,
      submit: () =>
        submitVoiceSkipLog(at, getCurrentSessionId(), getTodayKey()),
      successToast: "已进入下一步",
    });
  } finally {
    submitting.value = false;
  }
}

async function onSkip() {
  if (submitting.value) return;
  submitting.value = true;
  const at = Date.now();
  markVoiceSkipped({ reason: "user_skip" });
  endTaskTimer("voice");
  trackEvent("voice", "skip_voice", { at });
  try {
    await runStepSubmit({
      router,
      submit: () =>
        submitVoiceSkipLog(at, getCurrentSessionId(), getTodayKey()),
      successToast: "已跳过",
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

.prompt {
  white-space: pre-line;
  color: #606266;
  line-height: 1.6;
}

.hint {
  color: #909399;
  font-size: 13px;
}

.interval-alert {
  margin: 16px 0;
}

.record-panel {
  margin-top: 24px;
  text-align: center;
}

.btn-row {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}
</style>
