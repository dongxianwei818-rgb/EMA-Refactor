/** 模块 1：知情同意 */
var CONSENT_SECTIONS = [
  {
    title: "研究目的",
    content:
      "通过生态瞬时评估（EMA）连续监测大学生人们心理健康相关状态，支持早期风险识别与干预研究。",
  },
  {
    title: "采集哪些数据",
    content:
      "问卷、文本日记、语音、视频（可选不露脸）、微信运动步数、小程序使用行为等。",
  },
  {
    title: "数据用于什么",
    content: "仅用于科研，去标识化后用于统计分析与模型训练，不作为临床诊断。",
  },
  {
    title: "是否采集语音/视频",
    content:
      "是。语音建议每 2 天 30–60 秒；视频建议每 4 天 1 次，可选择不露脸。",
  },
  {
    title: "是否采集微信运动步数",
    content: "是。授权后获取步数及波动指标，用于活动水平分析。",
  },
  {
    title: "是否做心理风险预测",
    content: "研究团队可能构建风险预测模型，结果仅供科研与约定范围内的反馈。",
  },
  {
    title: "是否会向本人反馈",
    content: "可能提供简要状态反馈，具体形式以研究方案为准。",
  },
  {
    title: "是否会通知辅导员或心理中心",
    content:
      "仅在高风险且符合伦理与知情同意约定时，经评估后按预案联系校内相关部门。",
  },
  {
    title: "如何退出研究",
    content: "可随时申请退出，停止新数据采集；已采集数据按伦理要求处理。",
  },
  {
    title: "数据保存多久",
    content: "通常项目结束后保存 3–5 年，到期销毁或匿名归档。",
  },
  {
    title: "联系方式",
    content: "research@example.edu.cn（请替换为实际联系方式）",
  },
];

/** 模块 2：基线测评（仅研究编号，不采姓名学号） */
var BASELINE_SECTIONS = [
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

/** 模块 3：每日 EMA（0-10 分，控制在 30-60 秒） */
var EMA_QUESTIONS = [
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

/** 模块 4：日记提示语（轮换） */
var DIARY_PROMPTS = [
  "请用几句话描述你今天的状态。",
  "今天让你压力最大的一件事是什么？",
  "今天有没有让你感到开心或有成就感的事？",
  "如果用一个词形容今天，你会选什么？为什么？",
];

/** 模块 5：语音任务提示 */
var VOICE_PROMPTS = [
  "请用约 1 分钟说说你今天过得怎么样。",
  "今天有没有一件让你印象深刻的事？",
  "今天的压力主要来自哪里？",
  "最近睡眠怎么样？",
];

/** 模块 6：视频固定问题 */
var VIDEO_QUESTIONS = [
  "回想一件近期开心的小事，简单分享一下这件事？",
  "说说最近遇到的一件棘手、让你发愁的麻烦事？",
  "接下来我会描述一组客观信息，听到不符合认知的内容可以自然表达疑惑。",
  "客观聊聊自身对现在生活现状的满意程度？",
  "聊一聊自身短板与不足，你怎么看待自己的缺点？",
  "直面回答：有没有刻意隐瞒过某件相关事情？",
  "聊一件内心比较敏感、不愿对外提及的过往经历。",
  "分别分享一件人生里最欣喜、最委屈的经历。",
  "自由描述一整天从早到晚的作息与日常细节。",
];

var RANDOMQUESTION = "请选项任何一个或几个问题回答:";

/** 资源页：求助热线与自助内容（请按实际研究单位替换） */
var RESOURCE_SECTIONS = [
  {
    title: "紧急求助",
    hint: "如遇自伤或伤人风险，请立即寻求专业帮助",
    items: [
      { name: "全国心理援助热线", phone: "12356", desc: "24 小时" },
      {
        name: "北京心理危机研究与干预中心",
        phone: "010-82951332",
        desc: "24 小时",
      },
      { name: "生命热线", phone: "400-161-9995", desc: "24 小时" },
    ],
  },
  {
    title: "校内支持",
    hint: "以下为示例，请替换为本校心理中心信息",
    items: [
      {
        name: "校内心理中心预约",
        desc: "research@example.edu.cn",
        copyText: "research@example.edu.cn",
      },
      {
        name: "辅导员联系",
        desc: "高风险情况下，研究方可能按知情同意约定联系校内相关部门",
        phone: "010-82951332",
      },
    ],
  },
  {
    title: "自助练习",
    items: [
      {
        name: "4-7-8 呼吸放松",
        desc: "吸气 4 秒、屏息 7 秒、呼气 8 秒，重复 3–5 次，帮助缓解紧张与焦虑。",
      },
      {
        name: "Grounding 五感练习",
        desc: "依次说出 5 样看见、4 样触摸、3 样听见、2 样闻到、1 样尝到的事物，把注意力拉回当下。",
      },
      {
        name: "情绪日记提示",
        desc: "不必追求完美表达，用简短句子记录此刻感受即可，与每日 EMA 打卡相互补充。",
      },
    ],
  },
];

/** 后端 API 根地址，如 http://127.0.0.1:8000/api/v1 */
// var API_BASE_URL = "http://127.0.0.1:8000/api/v1";
var API_BASE_URL = "http://192.168.2.103:8000/api/v1";
var OPEN_ID = "0f1ffwll2gtyPh40gYml2wB0wl2ffwlv";

module.exports = {
  API_BASE_URL: API_BASE_URL,
  CONSENT_SECTIONS: CONSENT_SECTIONS,
  BASELINE_SECTIONS: BASELINE_SECTIONS,
  EMA_QUESTIONS: EMA_QUESTIONS,
  DIARY_PROMPTS: DIARY_PROMPTS,
  VOICE_PROMPTS: VOICE_PROMPTS,
  VIDEO_QUESTIONS: VIDEO_QUESTIONS,
  RANDOMQUESTION: RANDOMQUESTION,
  RESOURCE_SECTIONS: RESOURCE_SECTIONS,
  OPEN_ID: OPEN_ID,
  VIDEO_MIN_SEC: 5,
  VIDEO_MAX_SEC: 60,
  /** 语音录制最小间隔（天） */
  VOICE_INTERVAL_DAYS: 2,
  /** 视频录制最小间隔（天） */
  VIDEO_INTERVAL_DAYS: 4,
  EMA_TARGET_SEC: 60,
  DIARY_MIN: 30,
  DIARY_MAX: 100,
  VOICE_MIN_SEC: 5,
  VOICE_MAX_SEC: 60,
};
