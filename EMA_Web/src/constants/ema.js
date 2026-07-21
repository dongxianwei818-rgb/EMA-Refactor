/** 与 EMA_WeChat/utils/constants.js 对齐的 Web 端 EMA 常量 */

export const BASELINE_SECTIONS = [
  {
    id: "basic",
    title: "基本信息",
    hint: "仅填写研究编号，勿填姓名、学号、住址等可识别信息",
    fields: [
      { id: "researchId", label: "研究编号", required: true, type: "input" },
      {
        id: "age",
        label: "年龄",
        required: true,
        type: "input",
        inputType: "number",
      },
      { id: "grade", label: "年级", required: true, type: "input" },
      { id: "major", label: "专业大类", required: true, type: "input" },
      {
        id: "gender",
        label: "性别",
        required: true,
        type: "radio",
        options: ["男", "女", "其他", "不愿回答"],
      },
      {
        id: "onlyChild",
        label: "是否独生",
        required: true,
        type: "radio",
        options: ["是", "否", "不愿回答"],
      },
      {
        id: "housing",
        label: "住宿情况",
        required: true,
        type: "radio",
        options: ["宿舍", "校外", "在家", "其他"],
      },
    ],
  },
  {
    id: "academic",
    title: "学业压力",
    hint: "请根据最近一周的实际学习情况作答",
    items: [
      {
        id: "course_pressure",
        label: "课程压力",
        options: ["很低", "较低", "中等", "较高", "很高"],
      },
      {
        id: "exam_pressure",
        label: "考试压力",
        options: ["很低", "较低", "中等", "较高", "很高"],
      },
      {
        id: "gpa_pressure",
        label: "绩点压力",
        options: ["很低", "较低", "中等", "较高", "很高"],
      },
      {
        id: "job_pressure",
        label: "就业压力",
        options: ["很低", "较低", "中等", "较高", "很高"],
      },
    ],
  },
  {
    id: "lifestyle",
    title: "生活方式",
    hint: "请根据最近一周生活方式的实际感受作答",
    items: [
      {
        id: "sleep_habit",
        label: "睡眠习惯",
        options: ["很差", "较差", "一般", "较好", "很好"],
      },
      {
        id: "exercise_freq",
        label: "运动频率",
        options: ["几乎不", "每周1-2次", "每周3-4次", "每周5次以上"],
      },
      {
        id: "social_freq",
        label: "社交频率",
        options: ["很少", "较少", "一般", "较多", "很多"],
      },
    ],
  },
  {
    id: "scale",
    title: "心理量表（筛查简版）",
    hint: "完整版 PHQ-9/GAD-7 等由后台配置；此处为入组筛查题",
    items: [
      {
        id: "phq9_1",
        label: "PHQ-9：做事提不起劲或乐趣少",
        options: ["0天", "1-7天", "8-14天", "几乎每天"],
      },
      {
        id: "phq9_2",
        label: "PHQ-9：心情低落、沮丧",
        options: ["0天", "1-7天", "8-14天", "几乎每天"],
      },
      {
        id: "gad7_1",
        label: "GAD-7：紧张焦虑、难放松",
        options: ["没有", "几天", "一半以上", "几乎每天"],
      },
      {
        id: "gad7_2",
        label: "GAD-7：不能停止担心",
        options: ["没有", "几天", "一半以上", "几乎每天"],
      },
      {
        id: "pss_1",
        label: "PSS：感到无法控制生活中重要的事情",
        options: ["从不", "偶尔", "有时", "经常"],
      },
      {
        id: "isi_1",
        label: "ISI：入睡困难",
        options: ["无", "轻度", "中度", "重度"],
      },
      {
        id: "ucla_1",
        label: "UCLA 孤独感：缺乏陪伴感",
        options: ["从不", "很少", "有时", "经常"],
      },
    ],
  },
  {
    id: "risk",
    title: "风险信息",
    hint: "隐私项可选填；自伤相关条目请谨慎作答",
    items: [
      {
        id: "counsel_before",
        label: "既往心理咨询经历",
        options: ["无", "有", "不愿回答"],
        optional: true,
      },
      {
        id: "treatment_now",
        label: "是否正在心理治疗/用药",
        options: ["否", "是", "不愿回答"],
        optional: true,
      },
      {
        id: "self_harm",
        label: "近一月是否出现自伤想法（筛查）",
        options: ["否", "是", "不愿回答"],
        optional: true,
      },
    ],
  },
];

export const EMA_QUESTIONS = [
  { id: "mood", label: "今天心情如何？", type: "scale10" },
  { id: "stress", label: "今天压力多大？", type: "scale10" },
  { id: "anxiety", label: "今天焦虑程度？", type: "scale10" },
  { id: "lonely", label: "今天孤独感？", type: "scale10" },
  { id: "sleep", label: "今天睡眠质量？", type: "scale10" },
  { id: "fatigue", label: "今天疲劳程度？", type: "scale10" },
  { id: "function", label: "今天学习/生活功能受影响吗？", type: "scale10" },
  {
    id: "negative",
    label: "今天是否出现明显消极想法？",
    type: "ternary",
    options: ["是", "否", "不愿回答"],
  },
];

export const DIARY_PROMPTS = [
  "请用几句话描述你今天的状态。",
  "今天让你压力最大的一件事是什么？",
  "今天有没有让你感到开心或有成就感的事？",
  "如果用一个词形容今天，你会选什么？为什么？",
];

export const VOICE_PROMPTS = [
  "请用约 1 分钟说说你今天过得怎么样。",
  "今天有没有一件让你印象深刻的事？",
  "今天的压力主要来自哪里？",
  "最近睡眠怎么样？",
];

export const VIDEO_QUESTIONS = [
  "回想一件近期开心的小事，简单分享一下这件事？",
  "说说最近遇到的一件棘手、让你发愁的麻烦事？",
  "客观聊聊自身对现在生活现状的满意程度？",
  "聊一聊自身短板与不足，你怎么看待自己的缺点？",
  "自由描述一整天从早到晚的作息与日常细节。",
];

export const RANDOM_QUESTION = "请任选其中一个或几个问题回答：";

export const TASK_META = [
  {
    key: "questionnaire",
    name: "每日 EMA",
    desc: "8项 · 每日 EMA（约 30–60 秒）· 0–10 分 · 滑动选择 · 是后续模型的重要标签",
  },
  {
    key: "diary",
    name: "文本日记",
    desc: "请写 30–100 字（可提取情绪词、自我指向、压力事件等文本特征）",
  },
  {
    key: "voice",
    name: "语音任务",
    desc: "每 2 天 1 次 · 每次5-60秒 · 停止后自动进入下一步",
  },
  {
    key: "video",
    name: "视频任务",
    desc: "每 4 天 1 次 · 正脸自拍 · 不露脸 不遮挡 · 光线充足 · 停止后自动进入下一步",
  },
  {
    key: "steps",
    name: "运动步数",
    desc: "手动输入 · 个体化基线对比 · 与前一日步数对比。关注相对个人基线的偏离，而非绝对步数阈值；可以通过微信运动自动获取，或者手动输入今日步数；",
  },
];

export const VIDEO_MIN_SEC = 5;
export const VIDEO_MAX_SEC = 60;
export const VOICE_INTERVAL_DAYS = 2;
export const VIDEO_INTERVAL_DAYS = 4;
export const DIARY_MIN = 30;
export const DIARY_MAX = 100;
export const VOICE_MIN_SEC = 5;
export const VOICE_MAX_SEC = 60;

export const TASK_ORDER = ["questionnaire", "diary", "voice", "video", "steps"];

export const TASK_ROUTES = {
  questionnaire: "/ema/questionnaire",
  diary: "/ema/diary",
  voice: "/ema/voice",
  video: "/ema/video",
  steps: "/ema/steps",
};
