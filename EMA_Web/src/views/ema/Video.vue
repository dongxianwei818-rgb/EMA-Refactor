<template>
  <div class="ema-task-page">
    <el-card shadow="never">
      <h2>视频任务</h2>
      <p class="prompt">{{ question }}</p>
      <p class="hint">
        建议录制 {{ minSec }}–{{ maxSec }} 秒 · 正脸自拍 · 可选择不露脸
      </p>

      <el-alert
        v-if="intervalHint"
        :closable="false"
        type="warning"
        :title="intervalHint"
        show-icon
        class="interval-alert"
      />

      <div class="video-preview">
        <video
          v-show="phase === 'recording'"
          ref="videoEl"
          autoplay
          muted
          playsinline
          class="preview"
        />
        <div v-if="phase !== 'recording'" class="preview-placeholder">
          {{ recordText }}
        </div>
      </div>

      <el-checkbox v-model="hideFace" @change="onHideFaceToggle"
        >不露脸（使用后置摄像头提示）</el-checkbox
      >

      <div class="btn-row">
        <el-button
          v-if="phase === 'idle' || phase === 'recording'"
          :type="phase === 'recording' ? 'danger' : 'primary'"
          @click="toggleRecord"
        >
          {{ phase === "recording" ? "停止录制" : "开始录制" }}
        </el-button>
        <el-button v-if="phase !== 'submitting'" @click="onSkip"
          >跳过本次</el-button
        >
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  RANDOM_QUESTION,
  VIDEO_MAX_SEC,
  VIDEO_MIN_SEC,
  VIDEO_QUESTIONS,
} from "../../constants/ema";
import { submitVideoSkipLog, uploadVideoLog } from "../../api/ema";
import {
  ensureCheckinSession,
  getCurrentSessionId,
  getRecordingIntervalStatus,
  getTodayKey,
  markTaskDone,
  markVideoDone,
  markVideoSkipped,
  saveSubmission,
} from "../../utils/ema";
import { runStepSubmit } from "../../utils/emaFlow";
import { endTaskTimer, startTaskTimer, trackEvent } from "../../utils/tracker";

const router = useRouter();
const question = `${RANDOM_QUESTION}\n${VIDEO_QUESTIONS.join("\n")}`;
const minSec = VIDEO_MIN_SEC;
const maxSec = VIDEO_MAX_SEC;
const phase = ref("idle");
const recordText = ref("开始录制");
const duration = ref(0);
const hideFace = ref(false);
const submitting = ref(false);
const intervalHint = ref("");
const videoEl = ref(null);

let mediaRecorder = null;
let mediaStream = null;
let videoChunks = [];
let tickTimer = null;
let recordStart = 0;

onMounted(async () => {
  ensureCheckinSession();
  trackEvent("video", "view", {}, "/ema/video");
  startTaskTimer("video");
  const status = getRecordingIntervalStatus("video");
  if (!status.due) {
    intervalHint.value = `距上次视频录制未满 ${status.intervalDays} 天（还需约 ${status.daysRemaining} 天）`;
    try {
      await ElMessageBox.confirm(
        intervalHint.value + "。可直接进行下一步，或重新录制。",
        "视频间隔提醒",
        { confirmButtonText: "直接进行下一步", cancelButtonText: "重新录制" },
      );
      await skipToNext();
    } catch {
      trackEvent("video", "rer_record_interval");
    }
  }
});

onBeforeUnmount(() => {
  cleanupStream();
  clearTimers();
});

function clearTimers() {
  if (tickTimer) {
    clearInterval(tickTimer);
    tickTimer = null;
  }
}

function cleanupStream() {
  if (mediaRecorder?.state === "recording") {
    try {
      mediaRecorder.stop();
    } catch {
      /* ignore */
    }
  }
  mediaStream?.getTracks().forEach((t) => t.stop());
  mediaStream = null;
}

function onHideFaceToggle() {
  trackEvent("video", "hide_face_toggle", { hideFace: hideFace.value });
}

async function toggleRecord() {
  if (phase.value === "recording") {
    stopRecord();
    return;
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: hideFace.value ? "environment" : "user" },
      audio: true,
    });
    if (videoEl.value) {
      videoEl.value.srcObject = mediaStream;
    }
    videoChunks = [];
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) videoChunks.push(e.data);
    };
    mediaRecorder.onstop = () => finishRecord();
    recordStart = Date.now();
    phase.value = "recording";
    recordText.value = "录制中…";
    trackEvent("video", "record_start");
    mediaRecorder.start();
    tickTimer = setInterval(() => {
      const sec = Math.floor((Date.now() - recordStart) / 1000);
      duration.value = sec;
      recordText.value = `录制中 ${sec} 秒`;
      if (sec >= maxSec) stopRecord();
    }, 400);
  } catch {
    ElMessage.error("无法访问摄像头，请检查浏览器权限");
  }
}

function stopRecord() {
  clearTimers();
  if (mediaRecorder?.state === "recording") {
    phase.value = "processing";
    recordText.value = "处理中…";
    mediaRecorder.stop();
    mediaStream?.getTracks().forEach((t) => t.stop());
  }
}

function finishRecord() {
  const sec = duration.value || Math.floor((Date.now() - recordStart) / 1000);
  if (sec < minSec) {
    phase.value = "idle";
    recordText.value = "开始录制";
    ElMessage.warning(`至少录制 ${minSec} 秒`);
    return;
  }
  const blob = new Blob(videoChunks, { type: "video/webm" });
  const file = new File([blob], `video_${Date.now()}.webm`, {
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
  markTaskDone("video");
  markVideoDone();
  saveSubmission("video", {
    duration: sec,
    hideFace: hideFace.value,
    question,
  });
  endTaskTimer("video");
  trackEvent("video", "submit", { hideFace: hideFace.value, duration: sec });
  try {
    await runStepSubmit({
      router,
      submit: () =>
        uploadVideoLog(file, sec, at, getCurrentSessionId(), getTodayKey()),
      successToast: "已提交",
      onError: (err) => {
        phase.value = "idle";
        recordText.value = "开始录制";
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
  markTaskDone("video");
  saveSubmission("video", { skip: true, reason: "interval" }, { at });
  endTaskTimer("video");
  trackEvent("video", "skip_interval");
  try {
    await runStepSubmit({
      router,
      submit: () =>
        submitVideoSkipLog(at, getCurrentSessionId(), getTodayKey()),
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
  markVideoSkipped({ reason: "user_skip" });
  endTaskTimer("video");
  trackEvent("video", "skip_video", { at });
  try {
    await runStepSubmit({
      router,
      submit: () =>
        submitVideoSkipLog(at, getCurrentSessionId(), getTodayKey()),
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

.video-preview {
  margin: 16px 0;
  background: #1a1a1a;
  border-radius: 12px;
  overflow: hidden;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview {
  width: 100%;
  max-height: 320px;
  object-fit: cover;
}

.preview-placeholder {
  color: #ccc;
  padding: 40px;
  text-align: center;
}

.btn-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
</style>
