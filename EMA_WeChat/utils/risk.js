var ema = require('./ema');
var tracker = require('./tracker');

var LEVEL_META = {
  unknown: { label: '待评估', className: 'risk-unknown', summary: '数据不足，暂无法给出风险评估。' },
  low: { label: '低风险', className: 'risk-low', summary: '当前信号整体稳定，请继续保持规律打卡。' },
  medium: { label: '中等关注', className: 'risk-medium', summary: '部分指标出现波动，建议关注自身状态并善用资源页。' },
  high: { label: '需重点关注', className: 'risk-high', summary: '检测到较高风险信号，建议及时寻求支持或联系心理中心。' },
};

function getLatestQuestionnaire() {
  var list = ema.getSubmissions();
  for (var i = 0; i < list.length; i++) {
    if (list[i].type === 'questionnaire' && list[i].payload && list[i].payload.answers) {
      return list[i];
    }
  }
  return null;
}

function scoreBaseline(profile) {
  var score = 0;
  var factors = [];

  if (profile.self_harm === '是') {
    score += 4;
    factors.push({ label: '基线自伤想法筛查', value: '阳性', source: '基线测评' });
  }

  var phqHigh = profile.phq9_1 === '几乎每天' || profile.phq9_2 === '几乎每天';
  if (phqHigh) {
    score += 2;
    factors.push({ label: 'PHQ-9 筛查', value: '偏高', source: '基线测评' });
  }

  var gadHigh = profile.gad7_1 === '几乎每天' || profile.gad7_2 === '几乎每天';
  if (gadHigh) {
    score += 2;
    factors.push({ label: 'GAD-7 筛查', value: '偏高', source: '基线测评' });
  }

  if (profile.treatment_now === '是') {
    score += 1;
    factors.push({ label: '当前治疗/用药', value: '是', source: '基线测评' });
  }

  return { score: score, factors: factors };
}

function scoreRecentEma(answers) {
  var score = 0;
  var factors = [];
  if (!answers) return { score: 0, factors: [], alerts: [] };

  var alerts = [];
  var mood = Number(answers.mood);
  var stress = Number(answers.stress);
  var anxiety = Number(answers.anxiety);
  var lonely = Number(answers.lonely);
  var sleep = Number(answers.sleep);
  var fatigue = Number(answers.fatigue);
  var fn = Number(answers.function);

  if (!isNaN(mood) && mood <= 3) {
    score += 2;
    factors.push({ label: '今日心情', value: mood + '/10', source: 'EMA' });
    alerts.push({
      id: 'low_mood',
      level: 'warn',
      title: '心情偏低',
      desc: '今日心情评分较低（' + mood + '/10），建议适当休息或寻求支持。',
    });
  }

  if (!isNaN(stress) && stress >= 7) {
    score += 1;
    factors.push({ label: '今日压力', value: stress + '/10', source: 'EMA' });
    alerts.push({
      id: 'high_stress',
      level: 'warn',
      title: '压力偏高',
      desc: '今日压力评分较高（' + stress + '/10），可尝试呼吸放松等自助练习。',
    });
  }

  if (!isNaN(anxiety) && anxiety >= 7) {
    score += 2;
    factors.push({ label: '今日焦虑', value: anxiety + '/10', source: 'EMA' });
    alerts.push({
      id: 'high_anxiety',
      level: 'warn',
      title: '焦虑偏高',
      desc: '今日焦虑评分较高（' + anxiety + '/10），请关注身心状态。',
    });
  }

  if (answers.negative === '是') {
    score += 3;
    factors.push({ label: '消极想法', value: '是', source: 'EMA' });
    alerts.push({
      id: 'negative_thoughts',
      level: 'danger',
      title: '出现消极想法',
      desc: '今日报告出现明显消极想法，如有需要请使用资源页热线或联系心理中心。',
    });
  }

  if (!isNaN(lonely) && lonely >= 7) {
    score += 1;
    alerts.push({
      id: 'high_lonely',
      level: 'warn',
      title: '孤独感偏高',
      desc: '今日孤独感评分较高（' + lonely + '/10）。',
    });
  }

  if (!isNaN(sleep) && sleep <= 3) {
    score += 1;
    alerts.push({
      id: 'poor_sleep',
      level: 'warn',
      title: '睡眠质量偏低',
      desc: '今日睡眠质量评分较低（' + sleep + '/10）。',
    });
  }

  if (!isNaN(fatigue) && fatigue >= 7) {
    score += 1;
    alerts.push({
      id: 'high_fatigue',
      level: 'warn',
      title: '疲劳程度偏高',
      desc: '今日疲劳评分较高（' + fatigue + '/10）。',
    });
  }

  if (!isNaN(fn) && fn >= 7) {
    score += 1;
    alerts.push({
      id: 'low_function',
      level: 'warn',
      title: '功能受影响',
      desc: '今日学习/生活功能受影响程度较高（' + fn + '/10）。',
    });
  }

  return { score: score, factors: factors, alerts: alerts };
}

function collectBehaviorAlerts(stats, stepsAnalytics) {
  var alerts = [];
  var score = 0;

  if (stats.missedDays >= 3) {
    score += 2;
    alerts.push({
      id: 'missed_days',
      level: stats.missedDays >= 5 ? 'danger' : 'warn',
      title: '连续缺测',
      desc: '已连续 ' + stats.missedDays + ' 天未完成 EMA 打卡，缺测模式可能提示状态变化。',
    });
  }

  if (stepsAnalytics.lowDays >= 3) {
    score += 1;
    alerts.push({
      id: 'low_steps',
      level: 'warn',
      title: '步数持续偏低',
      desc: '已连续 ' + stepsAnalytics.lowDays + ' 天步数低于个人基线阈值。',
    });
  }

  if (stepsAnalytics.baseline && stepsAnalytics.deviation <= -40) {
    score += 1;
    alerts.push({
      id: 'steps_deviation',
      level: 'warn',
      title: '活动水平偏离基线',
      desc: '今日步数相对个人基线偏低约 ' + Math.abs(stepsAnalytics.deviation) + '%。',
    });
  }

  if (stats.videoSkips >= 3 || stats.voiceSkips >= 3) {
    score += 1;
    alerts.push({
      id: 'task_skip',
      level: 'warn',
      title: '任务跳过偏多',
      desc: '语音跳过 ' + stats.voiceSkips + ' 次，视频跳过 ' + stats.videoSkips + ' 次。',
    });
  }

  return { score: score, alerts: alerts };
}

function resolveLevel(totalScore, hasCritical) {
  if (hasCritical || totalScore >= 6) return 'high';
  if (totalScore >= 3) return 'medium';
  if (totalScore > 0) return 'low';
  return 'low';
}

function formatUpdateLabel(latestEma, hasBaseline) {
  if (latestEma && latestEma.date) return '更新于 ' + latestEma.date + ' EMA';
  if (hasBaseline) return '基于基线测评';
  return '暂无数据';
}

function getFutureDateLabel(offsetDays) {
  var d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return (d.getMonth() + 1) + '/' + d.getDate();
}

function getRecentEmaTrend() {
  var list = ema.getSubmissions();
  var byDate = {};
  list.forEach(function (item) {
    if (item.type !== 'questionnaire' || !item.date || !item.payload) return;
    if (!byDate[item.date] || (item.at && item.at > byDate[item.date].at)) {
      byDate[item.date] = item.payload.answers || {};
    }
  });
  var dates = Object.keys(byDate).sort();
  var recent = dates.slice(-7);
  var moodVals = [];
  var stressVals = [];
  recent.forEach(function (date) {
    var a = byDate[date];
    var mood = Number(a.mood);
    var stress = Number(a.stress);
    if (!isNaN(mood)) moodVals.push(mood);
    if (!isNaN(stress)) stressVals.push(stress);
  });
  var moodSlope = computeSlope(moodVals);
  var stressSlope = computeSlope(stressVals);
  var avgMood = avg(moodVals);
  var avgStress = avg(stressVals);
  return {
    moodSlope: moodSlope,
    stressSlope: stressSlope,
    avgMood: avgMood,
    avgStress: avgStress,
    dataDays: recent.length,
  };
}

function computeSlope(values) {
  if (!values || values.length < 2) return 0;
  var mid = Math.ceil(values.length / 2);
  var early = values.slice(0, mid);
  var late = values.slice(mid);
  return avg(late) - avg(early);
}

function avg(values) {
  if (!values || !values.length) return 0;
  var sum = 0;
  for (var i = 0; i < values.length; i++) sum += values[i];
  return sum / values.length;
}

function buildForecastSummary(trendLabel, level) {
  if (level === 'high') return '结合近期信号，未来一周需持续关注，建议主动寻求支持。';
  if (trendLabel === '上升') return '近期波动与行为模式显示，未来一周风险可能缓慢上升，请保持规律打卡。';
  if (trendLabel === '下降') return '近期状态有所改善，预计未来一周风险逐步回落。';
  return '基于当前基线与近期数据，预计未来一周风险整体平稳。';
}

function buildRiskForecast(currentScore, hasCritical, stats, emaTrend) {
  var days = [];
  var trendDelta = 0;
  if (emaTrend.moodSlope < -0.5) trendDelta += 0.4;
  if (emaTrend.stressSlope > 0.5) trendDelta += 0.5;
  if (stats.missedDays >= 3) trendDelta += 0.6;
  if (stats.missedDays >= 7) trendDelta += 0.4;

  var trendLabel = '平稳';
  if (trendDelta >= 0.8) trendLabel = '上升';
  else if (trendDelta <= -0.3 && emaTrend.moodSlope > 0.3) trendLabel = '下降';

  var peakLevel = 'low';
  for (var i = 1; i <= 7; i++) {
    var projected = currentScore + Math.round(trendDelta * i);
    if (stats.missedDays >= 3 && i <= 5) projected += 1;
    projected = Math.max(0, Math.min(15, projected));
    var critical = hasCritical && i <= 3;
    var level = resolveLevel(projected, critical);
    if (level === 'high') peakLevel = 'high';
    else if (level === 'medium' && peakLevel !== 'high') peakLevel = 'medium';
    var meta = LEVEL_META[level];
    days.push({
      dayIndex: i,
      dateLabel: getFutureDateLabel(i),
      score: projected,
      level: level,
      levelLabel: meta.label,
      levelClass: meta.className,
      barWidth: Math.round((projected / 15) * 100),
    });
  }

  return {
    days: days,
    trendLabel: trendLabel,
    summary: buildForecastSummary(trendLabel, peakLevel),
    peakLevelLabel: LEVEL_META[peakLevel].label,
    peakLevelClass: LEVEL_META[peakLevel].className,
    hasForecast: true,
  };
}

function getRiskAssessment() {
  var profile = ema.getProfile() || {};
  var hasBaseline = ema.hasBaseline();
  var latestEma = getLatestQuestionnaire();
  var stats = tracker.getBehaviorStats();
  var stepsAnalytics = ema.getStepsAnalytics();

  if (!hasBaseline && !latestEma) {
    var unknown = LEVEL_META.unknown;
    return {
      hasAssessment: false,
      current: {
        level: 'unknown',
        levelLabel: unknown.label,
        levelClass: unknown.className,
        score: 0,
        summary: unknown.summary,
        updatedLabel: '暂无数据',
        factors: [],
      },
      forecast: { hasForecast: false, days: [], summary: '', trendLabel: '', peakLevelLabel: '', peakLevelClass: '' },
      alerts: [],
      alertCount: 0,
    };
  }

  var baselinePart = scoreBaseline(profile);
  var emaPart = scoreRecentEma(latestEma ? latestEma.payload.answers : null);
  var behaviorPart = collectBehaviorAlerts(stats, stepsAnalytics);

  var totalScore = baselinePart.score + emaPart.score + behaviorPart.score;
  var allAlerts = (emaPart.alerts || []).concat(behaviorPart.alerts);
  var hasCritical = profile.self_harm === '是' || (latestEma && latestEma.payload.answers.negative === '是');
  var level = resolveLevel(totalScore, hasCritical);
  var meta = LEVEL_META[level];
  var emaTrend = getRecentEmaTrend();
  var forecast = buildRiskForecast(totalScore, hasCritical, stats, emaTrend);

  return {
    hasAssessment: true,
    current: {
      level: level,
      levelLabel: meta.label,
      levelClass: meta.className,
      score: totalScore,
      summary: meta.summary,
      updatedLabel: formatUpdateLabel(latestEma, hasBaseline),
      factors: baselinePart.factors.concat(emaPart.factors),
    },
    forecast: forecast,
    alerts: allAlerts,
    alertCount: allAlerts.length,
  };
}

module.exports = {
  getRiskAssessment: getRiskAssessment,
};
