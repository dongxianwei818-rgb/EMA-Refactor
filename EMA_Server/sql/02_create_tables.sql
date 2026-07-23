-- =============================================================================
-- EMA 服务端建表脚本（与 SQLAlchemy Web ORM 模型一致）
-- 用途：wechat / web / app 三端共用 ema_web 库表
-- 执行：先运行 01_create_database.sql，再对本脚本执行一次（USE ema_web）
-- （或直接运行 python scripts/init_db.py 初始化 ema_web）
-- =============================================================================

USE `ema_web`;

-- -----------------------------------------------------------------------------
-- 用户与授权
-- -----------------------------------------------------------------------------

-- users：研究参与者主表（三端统一：用户名/密码/角色）
CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '参与记录主键',
  `user_name` VARCHAR(64) NOT NULL COMMENT '登录用户名（可重复，按 id 区分参与轮次）',
  `psw` VARCHAR(128) NULL COMMENT '用户密码',
  `role` INT NULL DEFAULT 1 COMMENT '0=管理员；1 或空=普通用户',
  `research_id` VARCHAR(64) NULL COMMENT '研究编号，同一编号可有多轮参与记录',
  `login_count` INT NOT NULL DEFAULT 0 COMMENT '累计登录次数',
  `study_status` VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '研究状态：active / revoke / exited',
  `session_key` VARCHAR(128) NULL COMMENT '微信 session_key（可选）',
  `logout_at` DATETIME NULL COMMENT '退出研究时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '账号创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_users_user_name` (`user_name`),
  KEY `idx_users_research_id` (`research_id`),
  UNIQUE KEY `uk_users_id_research_id` (`id`, `research_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='研究参与者主表（三端共用）';

-- user_login_logs：用户登录流水（含终端类型）
CREATE TABLE IF NOT EXISTS `user_login_logs` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '登录记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `client_type` VARCHAR(16) NOT NULL DEFAULT 'web' COMMENT '终端类型：wechat / web / app',
  `logged_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
  `logout_at` DATETIME NULL COMMENT '登出时间',
  PRIMARY KEY (`id`),
  KEY `idx_login_log_user` (`user_id`),
  KEY `idx_login_log_client` (`client_type`),
  KEY `idx_login_log_user_time` (`user_id`, `logged_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户登录流水表';

-- consent_records：知情同意记录（遗留，exit 等场景）
-- 作用：记录退出研究等非 accept/revoke 操作；同意/撤销请使用 consent_authorization_logs。
CREATE TABLE IF NOT EXISTS `consent_records` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `action` VARCHAR(16) NOT NULL COMMENT '操作类型：accept/revoke/exit 等',
  `client_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '客户端操作时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_consent_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='知情同意遗留记录表';

-- consent_authorization_logs：知情同意与授权流水
-- 作用：每次用户同意或撤回知情同意/隐私授权时写入一条，含 openid、状态与事件详情。
CREATE TABLE IF NOT EXISTS `consent_authorization_logs` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `user_name` VARCHAR(64) NOT NULL COMMENT '登录用户名或 users.id 字符串（冗余）',
  `status` VARCHAR(16) NOT NULL COMMENT '状态：accept 同意 / revoke 撤销 / exit 退出',
  `event_info` JSON NOT NULL COMMENT '事件信息 JSON，如来源页面、操作渠道等',
  `client_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '客户端操作时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_consent_auth_user` (`user_id`),
  KEY `idx_consent_auth_user_name` (`user_name`),
  KEY `idx_consent_auth_user_time` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='知情同意与授权流水表';

-- baseline_profiles：基线测评档案
-- 作用：存储 onboarding 基线问卷各题项，按字段分列存储，便于查询与分析。
CREATE TABLE IF NOT EXISTS `baseline_profiles` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '档案主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id，每用户一条',
  `research_id` VARCHAR(64) NOT NULL COMMENT '研究编号（researchId），同一编号可有多轮基线档案',
  `age` INT NULL COMMENT '年龄',
  `grade` VARCHAR(32) NULL COMMENT '年级',
  `major` VARCHAR(64) NULL COMMENT '专业大类',
  `gender` VARCHAR(16) NULL COMMENT '性别',
  `only_child` VARCHAR(16) NULL COMMENT '是否独生（onlyChild）',
  `housing` VARCHAR(16) NULL COMMENT '住宿情况',
  `course_pressure` VARCHAR(16) NULL COMMENT '课程压力',
  `exam_pressure` VARCHAR(16) NULL COMMENT '考试压力',
  `gpa_pressure` VARCHAR(16) NULL COMMENT '绩点压力',
  `job_pressure` VARCHAR(16) NULL COMMENT '就业压力',
  `sleep_habit` VARCHAR(16) NULL COMMENT '睡眠习惯',
  `exercise_freq` VARCHAR(32) NULL COMMENT '运动频率',
  `social_freq` VARCHAR(16) NULL COMMENT '社交频率',
  `phq9_1` VARCHAR(16) NULL COMMENT 'PHQ-9：做事提不起劲或乐趣少',
  `phq9_2` VARCHAR(16) NULL COMMENT 'PHQ-9：心情低落、沮丧',
  `gad7_1` VARCHAR(16) NULL COMMENT 'GAD-7：紧张焦虑、难放松',
  `gad7_2` VARCHAR(16) NULL COMMENT 'GAD-7：不能停止担心',
  `pss_1` VARCHAR(16) NULL COMMENT 'PSS：感到无法控制生活中重要的事情',
  `isi_1` VARCHAR(16) NULL COMMENT 'ISI：入睡困难',
  `ucla_1` VARCHAR(16) NULL COMMENT 'UCLA 孤独感：缺乏陪伴感',
  `counsel_before` VARCHAR(16) NULL COMMENT '既往心理咨询经历',
  `treatment_now` VARCHAR(16) NULL COMMENT '是否正在心理治疗/用药',
  `self_harm` VARCHAR(16) NULL COMMENT '近一月自伤想法筛查',
  `completed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '完成时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_baseline_user` (`user_id`),
  KEY `idx_baseline_research_id` (`research_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='基线测评档案表';

-- -----------------------------------------------------------------------------
-- EMA 任务与提交数据
-- -----------------------------------------------------------------------------

-- submissions：EMA 任务提交记录
-- 作用：存储各类型任务（问卷、语音、视频、步数等）的提交内容与元数据，是核心采集表。
CREATE TABLE IF NOT EXISTS `submissions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '提交主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `submission_type` VARCHAR(32) NOT NULL COMMENT '任务类型：mood / voice / video / steps 等',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期，格式 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `payload` JSON NOT NULL COMMENT '提交内容 JSON',
  `client_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '客户端提交时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_submission` (`user_id`, `submission_type`, `task_date`, `session_id`, `client_at`),
  KEY `idx_submission_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='EMA 任务提交记录表';

-- ema_questions：每日 EMA 问卷回答
-- 作用：存储每日 EMA 打卡 8 项量表答案，各维度独立列便于分析与建模。
CREATE TABLE IF NOT EXISTS `ema_questions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `user_name` VARCHAR(64) NOT NULL COMMENT '登录用户名或 users.id 字符串（冗余）',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期，格式 YYYY-MM-DD',
  `answered_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '答题时间',
  `mood` INT NOT NULL COMMENT '心情 0-10',
  `stress` INT NOT NULL COMMENT '压力 0-10',
  `anxiety` INT NOT NULL COMMENT '焦虑 0-10',
  `lonely` INT NOT NULL COMMENT '孤独感 0-10',
  `sleep` INT NOT NULL COMMENT '睡眠质量 0-10',
  `fatigue` INT NOT NULL COMMENT '疲劳 0-10',
  `function` INT NOT NULL COMMENT '功能受影响 0-10',
  `negative` VARCHAR(16) NOT NULL COMMENT '消极想法：是/否/不愿回答',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_ema_question_user` (`user_id`),
  KEY `idx_ema_question_openid` (`openid`),
  KEY `idx_ema_question_user_time` (`user_id`, `answered_at`),
  KEY `idx_ema_question_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='每日 EMA 问卷回答表';

-- ema_diary：文本日志
-- 作用：存储每日文本日记内容及字数，供文本特征提取与情绪分析。
CREATE TABLE IF NOT EXISTS `ema_diary` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `user_name` VARCHAR(64) NOT NULL COMMENT '登录用户名或 users.id 字符串（冗余）',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期，格式 YYYY-MM-DD',
  `written_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `text` TEXT NOT NULL COMMENT '日记正文',
  `length` INT NOT NULL COMMENT '文本长度（字数）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_ema_diary_user` (`user_id`),
  KEY `idx_ema_diary_openid` (`openid`),
  KEY `idx_ema_diary_user_time` (`user_id`, `written_at`),
  KEY `idx_ema_diary_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='文本日志表';

-- ema_voice：语音录音记录
-- 作用：存储每日语音任务录音元数据，音频文件保存在服务端 files/voice 目录。
CREATE TABLE IF NOT EXISTS `ema_voice` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `user_name` VARCHAR(64) NOT NULL COMMENT '登录用户名或 users.id 字符串（冗余）',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期，格式 YYYY-MM-DD',
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '录音时间',
  `duration_sec` INT NOT NULL DEFAULT 0 COMMENT '录音时长（秒），跳过时为 0',
  `skip` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否跳过录音：0 否 / 1 是',
  `file_name` VARCHAR(255) NULL COMMENT '录音文件名，跳过时为空',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_ema_voice_user` (`user_id`),
  KEY `idx_ema_voice_openid` (`openid`),
  KEY `idx_ema_voice_user_time` (`user_id`, `recorded_at`),
  KEY `idx_ema_voice_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='语音录音记录表';

-- ema_video：视频录制记录
-- 作用：存储每日视频任务元数据，视频文件保存在服务端 files/video 目录。
CREATE TABLE IF NOT EXISTS `ema_video` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `user_name` VARCHAR(64) NOT NULL COMMENT '登录用户名或 users.id 字符串（冗余）',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期，格式 YYYY-MM-DD',
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '录制时间',
  `duration_sec` INT NOT NULL DEFAULT 0 COMMENT '视频时长（秒），跳过时为 0',
  `skip` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否跳过视频：0 否 / 1 是',
  `file_name` VARCHAR(255) NULL COMMENT '视频文件名，跳过时为空',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_ema_video_user` (`user_id`),
  KEY `idx_ema_video_openid` (`openid`),
  KEY `idx_ema_video_user_time` (`user_id`, `recorded_at`),
  KEY `idx_ema_video_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='视频录制记录表';

-- daily_task_snapshots：每日任务完成快照
-- 作用：同步小程序端当日各任务完成状态，用于首页展示与依从性统计。
CREATE TABLE IF NOT EXISTS `daily_task_snapshots` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '快照主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `tasks` JSON NOT NULL COMMENT '各任务完成状态 JSON',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_daily_task` (`user_id`, `task_date`, `session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='每日任务完成快照表';

-- steps_records：每日步数记录
-- 作用：存储微信运动或手动输入的每日步数，用于活动水平与偏离基线分析。
CREATE TABLE IF NOT EXISTS `steps_records` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '步数记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '日期',
  `steps` INT NOT NULL COMMENT '当日步数',
  `client_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_steps_day` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='每日步数记录表';

-- ema_step：步数打卡记录
-- 作用：存储每日步数任务提交（微信运动或手动输入），用于活动水平与相对基线分析。
CREATE TABLE IF NOT EXISTS `ema_step` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `user_name` VARCHAR(64) NOT NULL COMMENT '登录用户名或 users.id 字符串（冗余）',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期，格式 YYYY-MM-DD',
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `steps` INT NOT NULL COMMENT '当日步数',
  `source` VARCHAR(16) NOT NULL DEFAULT 'manual' COMMENT '来源：werun/manual/mock',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_ema_step_user` (`user_id`),
  KEY `idx_ema_step_openid` (`openid`),
  KEY `idx_ema_step_user_time` (`user_id`, `recorded_at`),
  KEY `idx_ema_step_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='步数打卡记录表';

-- skip_events：媒体任务跳过事件
-- 作用：记录视频/语音任务被跳过的次数、原因与时间，反映任务依从性与参与质量。
CREATE TABLE IF NOT EXISTS `skip_events` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '跳过事件主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `media_type` VARCHAR(16) NOT NULL COMMENT '媒体类型：video / voice',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '会话编号',
  `reason` VARCHAR(64) NOT NULL DEFAULT 'skip' COMMENT '跳过原因',
  `client_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '跳过时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_skip_event` (`user_id`, `media_type`, `client_at`),
  KEY `idx_skip_user_type` (`user_id`, `media_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='媒体任务跳过事件表';

-- -----------------------------------------------------------------------------
-- 打卡会话与行为追踪
-- -----------------------------------------------------------------------------

-- checkin_day_states：当日打卡状态
-- 作用：记录用户某天的打卡会话状态（当前 session、进度等），支持多次打卡场景。
CREATE TABLE IF NOT EXISTS `checkin_day_states` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '状态主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当前会话编号',
  `state_data` JSON NOT NULL COMMENT '打卡状态 JSON',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '状态更新时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_checkin_day` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='当日打卡状态表';

-- checkin_sessions：打卡会话明细
-- 作用：记录每次打卡会话的开始与完成时间，用于分析单次参与时长与完成率。
CREATE TABLE IF NOT EXISTS `checkin_sessions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '会话主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期',
  `session_id` INT NOT NULL COMMENT '会话编号',
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '会话开始时间',
  `completed_at` DATETIME NULL COMMENT '会话完成时间，未完成为 NULL',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_checkin_session` (`user_id`, `task_date`, `session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='打卡会话明细表';

-- video_done_events：视频完成事件
-- 作用：记录用户完成视频任务的次数与时间，辅助视频依从性统计。
CREATE TABLE IF NOT EXISTS `video_done_events` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '事件主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `client_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '完成时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_video_done_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='视频完成事件表';

-- behavior_logs：用户行为日志
-- 作用：采集页面浏览、按钮点击、任务耗时等行为事件，供后续行为特征提取。
CREATE TABLE IF NOT EXISTS `behavior_logs` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `module` VARCHAR(32) NOT NULL COMMENT '模块名，如 app / mood / steps',
  `action` VARCHAR(64) NOT NULL COMMENT '动作名，如 view / submit',
  `extra` JSON NULL COMMENT '附加参数 JSON',
  `route` VARCHAR(128) NULL COMMENT '页面路由',
  `hour` INT NULL COMMENT '发生时刻（小时，0-23）',
  `client_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '客户端时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务端入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_behavior_log` (`user_id`, `module`, `action`, `client_at`),
  KEY `idx_behavior_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户行为日志表';

-- behavior_meta：行为采集元信息
-- 作用：存储行为追踪的汇总元数据（如首次/末次上报时间），减少重复计算。
CREATE TABLE IF NOT EXISTS `behavior_meta` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '元信息主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id，每用户一条',
  `meta_data` JSON NOT NULL COMMENT '元信息 JSON',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_behavior_meta_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='行为采集元信息表';

-- -----------------------------------------------------------------------------
-- 多模态特征（分析流水线）
-- -----------------------------------------------------------------------------

-- text_features：文本特征
-- 作用：存储问卷/文本提交经 NLP 提取的特征向量，供风险模型输入；status 标记处理进度。
CREATE TABLE IF NOT EXISTS `text_features` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '特征主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `submission_id` BIGINT NULL COMMENT '关联 submissions.id，可为空（批量计算）',
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '处理状态：pending / done / failed',
  `features` JSON NULL COMMENT '提取的特征 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_text_feature_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='文本特征表';

-- voice_features：语音特征
-- 作用：存储语音任务经声学分析提取的特征，用于情绪与风险相关建模。
CREATE TABLE IF NOT EXISTS `voice_features` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '特征主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `submission_id` BIGINT NULL COMMENT '关联 submissions.id',
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '处理状态',
  `features` JSON NULL COMMENT '提取的特征 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_voice_feature_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='语音特征表';

-- video_features：视频特征
-- 作用：存储视频任务经视觉/面部分析提取的特征，供多模态融合分析。
CREATE TABLE IF NOT EXISTS `video_features` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '特征主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `submission_id` BIGINT NULL COMMENT '关联 submissions.id',
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '处理状态',
  `features` JSON NULL COMMENT '提取的特征 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_video_feature_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='视频特征表';

-- behavior_features：行为特征
-- 作用：由 behavior_logs 聚合计算的行为模式特征，反映使用规律与参与模式。
CREATE TABLE IF NOT EXISTS `behavior_features` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '特征主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '处理状态',
  `features` JSON NULL COMMENT '聚合特征 JSON',
  `computed_at` DATETIME NULL COMMENT '计算完成时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_behavior_feature_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='行为特征表';

-- questions_features：EMA 问卷趋势特征
-- 作用：对 ema_questions 七项 0-10 分量表计算 EMA 平滑趋势，供模型分析与干预决策。
CREATE TABLE IF NOT EXISTS `questions_features` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '特征主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `submission_id` BIGINT NULL COMMENT '关联 ema_questions.id',
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '处理状态：pending / done / failed',
  `features` JSON NULL COMMENT 'EMA 趋势特征 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_questions_feature_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='EMA 问卷趋势特征表';

-- step_features：微信运动步数特性
-- 作用：基于 ema_step 计算个体化步数基线、波动、连续低步数与周末/工作日节律等特征。
CREATE TABLE IF NOT EXISTS `step_features` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '特征主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `submission_id` BIGINT NULL COMMENT '关联 ema_step.id',
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '处理状态：pending / done / failed',
  `features` JSON NULL COMMENT '步数特性 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_step_feature_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='微信运动步数特性表';

-- -----------------------------------------------------------------------------
-- 风险预警与反馈
-- -----------------------------------------------------------------------------

-- risk_snapshots：风险评估快照
-- 作用：保存每次打卡完成后的当前风险、未来预测、异常预警，按 task_date + session_id 区分轮次。
CREATE TABLE IF NOT EXISTS `risk_snapshots` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '快照主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `snapshot_type` VARCHAR(32) NOT NULL COMMENT '类型：current / forecast / alerts',
  `result_data` JSON NOT NULL COMMENT '评估结果 JSON',
  `computed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_risk_snapshot` (`user_id`, `task_date`, `session_id`, `snapshot_type`),
  KEY `idx_risk_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='风险评估快照表';

-- feedback_records：非诊断性反馈记录
-- 作用：按 task_date + session_id 存储每轮打卡的反馈内容；Web 端录入，小程序端只读。
CREATE TABLE IF NOT EXISTS `feedback_records` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '反馈主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `task_date` VARCHAR(16) NOT NULL COMMENT '任务日期 YYYY-MM-DD',
  `session_id` INT NOT NULL DEFAULT 1 COMMENT '当日第几次打卡会话',
  `feedback_type` VARCHAR(32) NOT NULL DEFAULT 'non_diagnostic' COMMENT '反馈类型',
  `content` JSON NOT NULL COMMENT '反馈内容 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_feedback_session` (`user_id`, `task_date`, `session_id`, `feedback_type`),
  KEY `idx_feedback_user_date` (`user_id`, `task_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='非诊断性反馈记录表';

-- referral_records：高风险转介记录
-- 作用：记录需人工跟进的高风险个案转介状态，供研究团队或咨询师处理。
CREATE TABLE IF NOT EXISTS `referral_records` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '转介主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `risk_level` VARCHAR(16) NOT NULL COMMENT '触发转介时的风险等级',
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '处理状态：pending / handled 等',
  `note` TEXT NULL COMMENT '备注说明',
  `referred_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '转介时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_referral_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='高风险转介记录表';

-- chat_messages：EMA_Chat 非诊断对话消息
CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '消息主键',
  `user_id` BIGINT NOT NULL COMMENT '关联 users.id',
  `role` VARCHAR(16) NOT NULL COMMENT 'user / assistant / system / researcher',
  `content` TEXT NOT NULL COMMENT '消息正文',
  `meta` JSON NULL COMMENT '附加元数据',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_chat_user_time` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='EMA_Chat 对话消息表';
