var tracker = require("./tracker");

var MODULE_LABELS = {
  app: "应用",
  home: "首页",
  my: "我的",
  records: "记录",
  trends: "趋势",
  resources: "资源",
  consent: "知情同意",
  baseline: "基线测评",
  questionnaire: "EMA 问卷",
  diary: "文本日记",
  voice: "语音",
  video: "视频",
  steps: "步数",
  checkin: "打卡",
};

var ACTION_LABELS = {
  app_launch: "启动应用",
  view: "浏览页面",
  submit: "提交",
  accept: "同意授权",
  revoke: "撤回授权",
  review: "查看协议",
  session_complete: "完成打卡轮次",
  recheckin_start: "开始补打卡",
  start_flow: "开始打卡流程",
  start_task: "开始任务",
  task_duration: "任务耗时",
  skip_voice: "跳过语音",
  skip_video: "跳过视频",
  skip_interval: "跳过间隔限制",
  rer_record_interval: "重新录制（间隔）",
  record_start: "开始录制",
  hide_face_toggle: "切换不露脸",
};

var SUMMARY_ID_BY_LABEL = {
  行为记录总数: "tone0",
  打开次数: "openCount",
  今日已完成打卡轮次: "tone1",
  连续缺测天数: "missedDays",
  补打卡次数: "tone2",
  平均日记字数: "avgDiary",
  "平均语音时长(秒)": "avgVoice",
  "平均视频时长(秒)": "avgVideo",
  语音跳过次数: "voiceSkips",
  视频跳过次数: "videoSkips",
};

function formatDateTime(ts) {
  if (!ts) return "";
  var d = new Date(ts);
  var pad = function (n) {
    return n < 10 ? "0" + n : "" + n;
  };
  return (
    d.getFullYear() +
    "-" +
    pad(d.getMonth() + 1) +
    "-" +
    pad(d.getDate()) +
    " " +
    pad(d.getHours()) +
    ":" +
    pad(d.getMinutes()) +
    ":" +
    pad(d.getSeconds())
  );
}

function moduleLabel(module) {
  return MODULE_LABELS[module] || module || "未知";
}

function actionLabel(action) {
  return ACTION_LABELS[action] || action || "未知";
}

function formatExtra(extra) {
  if (!extra || typeof extra !== "object") return "";
  var keys = Object.keys(extra);
  if (!keys.length) return "";
  return keys
    .map(function (k) {
      var v = extra[k];
      if (v === null || v === undefined || v === "") return "";
      if (typeof v === "object") return k + ": " + JSON.stringify(v);
      return k + ": " + v;
    })
    .filter(Boolean)
    .join("；");
}

function formatLogSummary(log) {
  var parts = [moduleLabel(log.module), actionLabel(log.action)];
  var extra = formatExtra(log.extra);
  if (extra) parts.push(extra);
  if (log.route) parts.push("页面: " + log.route);
  if (log.hour != null) parts.push("时段: " + log.hour + " 时");
  return parts.join(" · ");
}

function pushRows(rows, label, value, idHint) {
  if (value === undefined || value === null || value === "") return;
  var id =
    idHint ||
    SUMMARY_ID_BY_LABEL[label] ||
    "tone" + (rows.length % 10);
  rows.push({ id: id, label: label, value: String(value) });
}

function buildBehaviorDetailSections() {
  var stats = tracker.getBehaviorStats();
  var meta = tracker.getBehaviorMeta();
  var logs = tracker.getBehaviorLogs();
  var sections = [];

  var summaryRows = [];
  pushRows(summaryRows, "行为记录总数", stats.total);
  pushRows(summaryRows, "打开次数", stats.openCount);
  pushRows(summaryRows, "今日已完成打卡轮次", stats.todaySessions);
  pushRows(summaryRows, "连续缺测天数", stats.missedDays);
  pushRows(summaryRows, "补打卡次数", stats.recheckinCount);
  pushRows(summaryRows, "平均日记字数", stats.avgDiaryWords);
  pushRows(summaryRows, "平均语音时长(秒)", stats.avgVoiceSec);
  pushRows(summaryRows, "平均视频时长(秒)", stats.avgVideoSec);
  pushRows(summaryRows, "语音跳过次数", stats.voiceSkips);
  pushRows(summaryRows, "视频跳过次数", stats.videoSkips);
  if (summaryRows.length) {
    sections.push({ id: "summary", title: "行为概览", rows: summaryRows });
  }

  var moduleKeys = stats.byModule ? Object.keys(stats.byModule) : [];
  if (moduleKeys.length) {
    moduleKeys.sort(function (a, b) {
      return stats.byModule[b] - stats.byModule[a];
    });
    sections.push({
      id: "byModule",
      title: "模块行为统计",
      rows: moduleKeys.map(function (key, index) {
        return {
          id: "tone" + (index % 10),
          label: moduleLabel(key),
          value: stats.byModule[key] + " 次",
        };
      }),
    });
  }

  var checkinRows = [];
  (meta.checkinTimes || []).forEach(function (item, index) {
    pushRows(
      checkinRows,
      "问卷提交 " + (index + 1),
      formatDateTime(item.at) +
        "（" +
        item.hour +
        " 时，第 " +
        (item.sessionId || 1) +
        " 轮）",
      "tone" + (index % 10)
    );
  });
  (meta.checkinSessions || []).forEach(function (item, index) {
    pushRows(
      checkinRows,
      "完成轮次 " + (index + 1),
      formatDateTime(item.at) + (item.date ? "（" + item.date + "）" : ""),
      "tone" + ((index + 3) % 10)
    );
  });
  if (checkinRows.length) {
    sections.push({ id: "checkin", title: "打卡行为", rows: checkinRows });
  }

  var diaryRows = [];
  (meta.diaryWordCounts || []).forEach(function (count, index) {
    pushRows(diaryRows, "日记 " + (index + 1), count + " 字", "avgDiary");
  });
  if (diaryRows.length) {
    sections.push({ id: "diary", title: "日记行为", rows: diaryRows });
  }

  var voiceRows = [];
  (meta.voiceDurations || []).forEach(function (sec, index) {
    pushRows(voiceRows, "录音 " + (index + 1), sec + " 秒", "avgVoice");
  });
  (stats.voiceSkipRecords || []).forEach(function (item, index) {
    pushRows(
      voiceRows,
      "跳过记录 " + (index + 1),
      formatDateTime(item.at || item),
      "voiceSkips"
    );
  });
  if (voiceRows.length) {
    sections.push({ id: "voice", title: "语音行为", rows: voiceRows });
  }

  var videoRows = [];
  (meta.videoDurations || []).forEach(function (sec, index) {
    pushRows(videoRows, "录制 " + (index + 1), sec + " 秒", "avgVideo");
  });
  (stats.videoSkipRecords || []).forEach(function (item, index) {
    pushRows(
      videoRows,
      "跳过记录 " + (index + 1),
      formatDateTime(item.at || item),
      "videoSkips"
    );
  });
  if (videoRows.length) {
    sections.push({ id: "video", title: "视频行为", rows: videoRows });
  }

  var taskRows = [];
  (meta.taskDurations || []).forEach(function (item, index) {
    var ms = item && item.ms != null ? item.ms : item;
    var route = item && item.route ? "（" + item.route + "）" : "";
    var sec = typeof ms === "number" ? Math.round(ms / 100) / 10 : ms;
    pushRows(
      taskRows,
      "任务 " + (index + 1),
      sec + " 秒" + route,
      "tone" + (index % 10)
    );
  });
  if (taskRows.length) {
    sections.push({ id: "task", title: "任务耗时", rows: taskRows });
  }

  return {
    sections: sections,
    logs: logs.map(function (log, index) {
      return {
        id: index,
        time: formatDateTime(log.at),
        summary: formatLogSummary(log),
      };
    }),
  };
}

module.exports = {
  buildBehaviorDetailSections: buildBehaviorDetailSections,
};
