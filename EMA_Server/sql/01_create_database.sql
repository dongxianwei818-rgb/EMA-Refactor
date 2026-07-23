-- 建库脚本：仅创建共享业务库 ema_web 与用户 dxw
-- 使用 root 账户执行
-- wechat / web / app 三端统一使用 ema_web

CREATE DATABASE IF NOT EXISTS `ema_web`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'dxw'@'%' IDENTIFIED BY '1qaz!QAZ';
CREATE USER IF NOT EXISTS 'dxw'@'localhost' IDENTIFIED BY '1qaz!QAZ';

GRANT ALL PRIVILEGES ON `ema_web`.* TO 'dxw'@'%';
GRANT ALL PRIVILEGES ON `ema_web`.* TO 'dxw'@'localhost';
FLUSH PRIVILEGES;
