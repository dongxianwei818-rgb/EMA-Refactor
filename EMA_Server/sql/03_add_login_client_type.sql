-- 已有 ema_web 库时：为 user_login_logs 增加 client_type
USE `ema_web`;

ALTER TABLE `user_login_logs`
  ADD COLUMN IF NOT EXISTS `client_type` VARCHAR(16) NOT NULL DEFAULT 'web'
    COMMENT '终端类型：wechat / web / app' AFTER `user_id`;

-- MySQL 8.0.12 前无 IF NOT EXISTS 时可用下方手工检查方式：
-- ALTER TABLE user_login_logs ADD COLUMN client_type VARCHAR(16) NOT NULL DEFAULT 'web' AFTER user_id;

CREATE INDEX IF NOT EXISTS `idx_login_log_client` ON `user_login_logs` (`client_type`);
