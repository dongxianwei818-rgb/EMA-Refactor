-- 建库脚本：创建 ema / ema_web / ema_app 与用户 dxw
-- 使用 root 账户执行
-- wechat → ema，web → ema_web，app → ema_app

CREATE DATABASE IF NOT EXISTS `ema`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `ema_web`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `ema_app`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'dxw'@'%' IDENTIFIED BY '1qaz!QAZ';
CREATE USER IF NOT EXISTS 'dxw'@'localhost' IDENTIFIED BY '1qaz!QAZ';

GRANT ALL PRIVILEGES ON `ema`.* TO 'dxw'@'%';
GRANT ALL PRIVILEGES ON `ema`.* TO 'dxw'@'localhost';
GRANT ALL PRIVILEGES ON `ema_web`.* TO 'dxw'@'%';
GRANT ALL PRIVILEGES ON `ema_web`.* TO 'dxw'@'localhost';
GRANT ALL PRIVILEGES ON `ema_app`.* TO 'dxw'@'%';
GRANT ALL PRIVILEGES ON `ema_app`.* TO 'dxw'@'localhost';
FLUSH PRIVILEGES;
