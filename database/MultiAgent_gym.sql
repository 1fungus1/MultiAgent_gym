/*
 MultiAgent_gym - MySQL 8.0 demo database

 Demo accounts:
   admin / 123456
   zhangsan / 123456

 All member cards are active and expire on 2026-12-31.
 All courses and coaches are active.
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS multiagent_gym
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE multiagent_gym;

DROP TABLE IF EXISTS `notification`;
DROP TABLE IF EXISTS `appointment_action_log`;
DROP TABLE IF EXISTS `appointment`;
DROP TABLE IF EXISTS `course`;
DROP TABLE IF EXISTS `coach`;
DROP TABLE IF EXISTS `sys_user`;
DROP TABLE IF EXISTS `member`;

CREATE TABLE `member` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(50) NOT NULL,
  `phone` VARCHAR(20) NULL,
  `gender` VARCHAR(10) NULL,
  `age` INT NULL,
  `card_type` VARCHAR(30) NULL,
  `expire_time` DATE NULL,
  `status` TINYINT NOT NULL DEFAULT 1,
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_member_name` (`name`),
  KEY `idx_member_phone` (`phone`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `sys_user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `role` VARCHAR(20) NOT NULL,
  `related_id` BIGINT NULL,
  `status` TINYINT NOT NULL DEFAULT 1,
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sys_user_username` (`username`),
  KEY `idx_sys_user_related_id` (`related_id`),
  CONSTRAINT `fk_sys_user_member`
    FOREIGN KEY (`related_id`) REFERENCES `member` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `coach` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(50) NOT NULL,
  `phone` VARCHAR(20) NULL,
  `specialty` VARCHAR(100) NULL,
  `entry_date` DATE NULL,
  `status` TINYINT NOT NULL DEFAULT 1,
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `course` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `type` VARCHAR(50) NULL,
  `coach_id` BIGINT NULL,
  `start_time` DATETIME NULL,
  `end_time` DATETIME NULL,
  `capacity` INT NOT NULL DEFAULT 20,
  `booked_count` INT NOT NULL DEFAULT 0,
  `status` TINYINT NOT NULL DEFAULT 1,
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_course_coach_start` (`coach_id`, `start_time`),
  KEY `idx_course_status_start` (`status`, `start_time`),
  CONSTRAINT `fk_course_coach`
    FOREIGN KEY (`coach_id`) REFERENCES `coach` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `appointment` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `member_id` BIGINT NOT NULL,
  `course_id` BIGINT NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'reserved',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member_course` (`member_id`, `course_id`),
  KEY `idx_appointment_course_status` (`course_id`, `status`),
  CONSTRAINT `fk_appointment_member`
    FOREIGN KEY (`member_id`) REFERENCES `member` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_appointment_course`
    FOREIGN KEY (`course_id`) REFERENCES `course` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=69 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `appointment_action_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `appointment_id` BIGINT NOT NULL,
  `member_id` BIGINT NOT NULL,
  `course_id` BIGINT NOT NULL,
  `target_course_id` BIGINT NULL,
  `action` VARCHAR(20) NOT NULL,
  `detail` VARCHAR(255) NULL,
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_appointment_log_create_time` (`create_time`),
  KEY `idx_appointment_log_member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `notification` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `member_id` BIGINT NULL,
  `type` VARCHAR(30) NOT NULL,
  `title` VARCHAR(100) NOT NULL,
  `content` VARCHAR(500) NOT NULL,
  `related_id` BIGINT NULL,
  `is_read` TINYINT(1) NOT NULL DEFAULT 0,
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_notification_user_read` (`user_id`, `is_read`),
  KEY `idx_notification_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `member`
  (`id`, `name`, `phone`, `gender`, `age`, `card_type`, `expire_time`, `status`, `create_time`, `update_time`)
VALUES
  (1,  '张清和', '13810001001', '男', 28, '年卡', '2026-12-31', 1, '2026-09-01 09:10:00', '2026-11-03 10:00:00'),
  (2,  '林知夏', '13810001002', '女', 26, '季卡', '2026-12-31', 1, '2026-09-03 10:20:00', '2026-11-03 10:00:00'),
  (3,  '顾言川', '13810001003', '男', 32, '年卡', '2026-12-31', 1, '2026-09-08 14:30:00', '2026-11-03 10:00:00'),
  (4,  '苏晚晴', '13810001004', '女', 30, '年卡', '2026-12-31', 1, '2026-09-12 16:40:00', '2026-11-03 10:00:00'),
  (5,  '陆景行', '13810001005', '男', 27, '月卡', '2026-12-31', 1, '2026-09-18 11:15:00', '2026-11-03 10:00:00'),
  (6,  '江语柔', '13810001006', '女', 24, '季卡', '2026-12-31', 1, '2026-09-21 18:25:00', '2026-11-03 10:00:00'),
  (7,  '周亦辰', '13810001007', '男', 29, '年卡', '2026-12-31', 1, '2026-09-25 08:50:00', '2026-11-03 10:00:00'),
  (8,  '许安澜', '13810001008', '女', 31, '年卡', '2026-12-31', 1, '2026-09-28 13:35:00', '2026-11-03 10:00:00'),
  (9,  '陈屿森', '13810001009', '男', 35, '年卡', '2026-12-31', 1, '2026-10-02 09:05:00', '2026-11-03 10:00:00'),
  (10, '唐若溪', '13810001010', '女', 25, '季卡', '2026-12-31', 1, '2026-10-05 15:45:00', '2026-11-03 10:00:00'),
  (11, '宋知远', '13810001011', '男', 33, '年卡', '2026-12-31', 1, '2026-10-08 20:10:00', '2026-11-03 10:00:00'),
  (12, '叶书宁', '13810001012', '女', 28, '月卡', '2026-12-31', 1, '2026-10-12 12:30:00', '2026-11-03 10:00:00'),
  (13, '方以航', '13810001013', '男', 22, '季卡', '2026-12-31', 1, '2026-10-15 17:20:00', '2026-11-03 10:00:00'),
  (14, '夏沐阳', '13810001014', '男', 26, '年卡', '2026-12-31', 1, '2026-10-18 07:55:00', '2026-11-03 10:00:00'),
  (15, '秦若岚', '13810001015', '女', 29, '年卡', '2026-12-31', 1, '2026-10-21 19:10:00', '2026-11-03 10:00:00'),
  (16, '温予安', '13810001016', '女', 23, '月卡', '2026-12-31', 1, '2026-10-24 10:40:00', '2026-11-03 10:00:00'),
  (17, '程嘉树', '13810001017', '男', 30, '年卡', '2026-12-31', 1, '2026-10-27 14:05:00', '2026-11-03 10:00:00'),
  (18, '黎星遥', '13810001018', '女', 27, '季卡', '2026-12-31', 1, '2026-10-30 16:35:00', '2026-11-03 10:00:00');

INSERT INTO `sys_user`
  (`id`, `username`, `password`, `role`, `related_id`, `status`, `create_time`, `update_time`)
VALUES
  (1, 'admin', '$argon2id$v=19$m=65536,t=3,p=4$8icsPnkC0ZsxB4oAGW2RHg$JK+S16W3LgrlpSYCK1tUFHOb25gXbMXBn1GwUdnra3U', 'admin', NULL, 1, '2026-07-08 09:24:53', '2026-11-02 20:30:31'),
  (2, 'zhangsan', '$argon2id$v=19$m=65536,t=3,p=4$LeVN1a4dypSMF9EZaa32oQ$N9A4VC6iEG7KV8zxfFoSU6Zyh5hWt9RAayTDryluZQU', 'member', 1, 1, '2026-07-08 09:24:53', '2026-11-02 20:32:27');

INSERT INTO `coach`
  (`id`, `name`, `phone`, `specialty`, `entry_date`, `status`, `create_time`, `update_time`)
VALUES
  (1, '沈知行', '13720001001', '功能性训练、体态矫正', '2022-03-15', 1, '2026-10-01 09:00:00', '2026-11-03 09:00:00'),
  (2, '林若溪', '13720001002', '普拉提、核心塑形', '2021-09-06', 1, '2026-10-01 09:05:00', '2026-11-03 09:00:00'),
  (3, '周启航', '13720001003', '力量训练、增肌计划', '2023-02-20', 1, '2026-10-01 09:10:00', '2026-11-03 09:00:00'),
  (4, '苏曼宁', '13720001004', '瑜伽、柔韧恢复', '2020-06-12', 1, '2026-10-01 09:15:00', '2026-11-03 09:00:00'),
  (5, '陆骁', '13720001005', '搏击操、有氧减脂', '2022-11-01', 1, '2026-10-01 09:20:00', '2026-11-03 09:00:00'),
  (6, '叶青禾', '13720001006', '动感单车、心肺训练', '2024-01-08', 1, '2026-10-01 09:25:00', '2026-11-03 09:00:00'),
  (7, '江远川', '13720001007', '运动康复、关节稳定', '2019-08-19', 1, '2026-10-01 09:30:00', '2026-11-03 09:00:00'),
  (8, '唐予安', '13720001008', '舞蹈健身、形体训练', '2023-07-10', 1, '2026-10-01 09:35:00', '2026-11-03 09:00:00');

INSERT INTO `course`
  (`id`, `name`, `type`, `coach_id`, `start_time`, `end_time`, `capacity`, `booked_count`, `status`, `create_time`, `update_time`)
VALUES
  (1,  '晨间唤醒瑜伽',     '瑜伽',       4, '2026-12-03 07:30:00', '2026-12-03 08:30:00', 16, 0, 1, '2026-10-28 09:00:00', '2026-11-03 09:00:00'),
  (2,  '核心普拉提塑形',   '普拉提',     2, '2026-12-03 10:00:00', '2026-12-03 11:00:00', 12, 0, 1, '2026-10-28 09:05:00', '2026-11-03 09:00:00'),
  (3,  '燃脂搏击操',       '搏击操',     5, '2026-12-03 19:00:00', '2026-12-03 20:00:00', 20, 0, 1, '2026-10-28 09:10:00', '2026-11-03 09:00:00'),
  (4,  '杠铃基础力量',     '力量训练',   3, '2026-12-04 18:30:00', '2026-12-04 19:30:00', 14, 0, 1, '2026-10-28 09:15:00', '2026-11-03 09:00:00'),
  (5,  '动感单车耐力骑行', '动感单车',   6, '2026-12-04 19:30:00', '2026-12-04 20:20:00', 18, 0, 1, '2026-10-28 09:20:00', '2026-11-03 09:00:00'),
  (6,  '肩颈舒缓拉伸',     '拉伸恢复',   4, '2026-12-05 09:30:00', '2026-12-05 10:20:00', 15, 0, 1, '2026-10-28 09:25:00', '2026-11-03 09:00:00'),
  (7,  '全身功能性训练',   '功能训练',   1, '2026-12-05 16:00:00', '2026-12-05 17:00:00', 16, 0, 1, '2026-10-28 09:30:00', '2026-11-03 09:00:00'),
  (8,  '力量塑形进阶',     '力量训练',   3, '2026-12-06 10:00:00', '2026-12-06 11:00:00', 12, 0, 1, '2026-10-28 09:35:00', '2026-11-03 09:00:00'),
  (9,  '有氧舞蹈燃脂',     '舞蹈健身',   8, '2026-12-06 15:00:00', '2026-12-06 16:00:00', 20, 0, 1, '2026-10-28 09:40:00', '2026-11-03 09:00:00'),
  (10, '髋膝稳定性训练',   '功能训练',   7, '2026-12-07 18:00:00', '2026-12-07 19:00:00', 10, 0, 1, '2026-10-28 09:45:00', '2026-11-03 09:00:00'),
  (11, '普拉提器械基础',   '普拉提',     2, '2026-12-08 19:00:00', '2026-12-08 20:00:00', 8,  0, 1, '2026-10-29 09:00:00', '2026-11-03 09:00:00'),
  (12, 'HIIT 间歇燃脂',    'HIIT',       5, '2026-12-09 18:30:00', '2026-12-09 19:15:00', 18, 0, 1, '2026-10-29 09:05:00', '2026-11-03 09:00:00'),
  (13, '流瑜伽舒展',       '瑜伽',       4, '2026-12-10 20:00:00', '2026-12-10 21:00:00', 16, 0, 1, '2026-10-29 09:10:00', '2026-11-03 09:00:00'),
  (14, '脊柱灵活训练',     '功能训练',   7, '2026-12-12 10:30:00', '2026-12-12 11:20:00', 12, 0, 1, '2026-10-29 09:15:00', '2026-11-03 09:00:00'),
  (15, '壶铃燃脂循环',     '力量训练',   3, '2026-12-13 09:00:00', '2026-12-13 10:00:00', 14, 0, 1, '2026-10-29 09:20:00', '2026-11-03 09:00:00'),
  (16, '单车冲刺挑战',     '动感单车',   6, '2026-12-14 19:00:00', '2026-12-14 19:50:00', 20, 0, 1, '2026-10-29 09:25:00', '2026-11-03 09:00:00'),
  (17, '形体芭蕾基础',     '形体训练',   8, '2026-12-16 19:30:00', '2026-12-16 20:30:00', 14, 0, 1, '2026-10-29 09:30:00', '2026-11-03 09:00:00'),
  (18, '晚间深度放松',     '拉伸恢复',   4, '2026-12-18 20:00:00', '2026-12-18 21:00:00', 16, 0, 1, '2026-10-29 09:35:00', '2026-11-03 09:00:00'),
  (19, '增肌力量循环',     '力量训练',   3, '2026-12-19 18:30:00', '2026-12-19 19:30:00', 12, 0, 1, '2026-10-29 09:40:00', '2026-11-03 09:00:00'),
  (20, '周末全身燃脂',     '有氧训练',   1, '2026-12-21 15:00:00', '2026-12-21 16:00:00', 20, 0, 1, '2026-10-29 09:45:00', '2026-11-03 09:00:00');

INSERT INTO `appointment`
  (`member_id`, `course_id`, `status`, `create_time`, `update_time`)
VALUES
  (2, 1, 'reserved', '2026-11-03 10:10:00', '2026-11-03 10:10:00'),
  (6, 1, 'reserved', '2026-11-03 10:11:00', '2026-11-03 10:11:00'),
  (10, 1, 'reserved', '2026-11-03 10:12:00', '2026-11-03 10:12:00'),
  (1, 2, 'reserved', '2026-11-03 10:15:00', '2026-11-03 10:15:00'),
  (4, 2, 'reserved', '2026-11-03 10:16:00', '2026-11-03 10:16:00'),
  (1, 3, 'reserved', '2026-11-03 10:20:00', '2026-11-03 10:20:00'),
  (5, 3, 'reserved', '2026-11-03 10:21:00', '2026-11-03 10:21:00'),
  (9, 3, 'reserved', '2026-11-03 10:22:00', '2026-11-03 10:22:00'),
  (13, 3, 'reserved', '2026-11-03 10:23:00', '2026-11-03 10:23:00'),
  (3, 4, 'reserved', '2026-11-03 10:25:00', '2026-11-03 10:25:00'),
  (7, 4, 'reserved', '2026-11-03 10:26:00', '2026-11-03 10:26:00'),
  (12, 4, 'reserved', '2026-11-03 10:27:00', '2026-11-03 10:27:00'),
  (2, 5, 'reserved', '2026-11-03 10:30:00', '2026-11-03 10:30:00'),
  (5, 5, 'reserved', '2026-11-03 10:31:00', '2026-11-03 10:31:00'),
  (8, 5, 'reserved', '2026-11-03 10:32:00', '2026-11-03 10:32:00'),
  (10, 5, 'reserved', '2026-11-03 10:33:00', '2026-11-03 10:33:00'),
  (14, 5, 'reserved', '2026-11-03 10:34:00', '2026-11-03 10:34:00'),
  (1, 6, 'reserved', '2026-11-03 10:35:00', '2026-11-03 10:35:00'),
  (6, 6, 'reserved', '2026-11-03 10:36:00', '2026-11-03 10:36:00'),
  (9, 6, 'reserved', '2026-11-03 10:37:00', '2026-11-03 10:37:00'),
  (15, 6, 'reserved', '2026-11-03 10:38:00', '2026-11-03 10:38:00'),
  (4, 7, 'reserved', '2026-11-03 10:40:00', '2026-11-03 10:40:00'),
  (11, 7, 'reserved', '2026-11-03 10:41:00', '2026-11-03 10:41:00'),
  (7, 8, 'reserved', '2026-11-03 10:43:00', '2026-11-03 10:43:00'),
  (12, 8, 'reserved', '2026-11-03 10:44:00', '2026-11-03 10:44:00'),
  (16, 8, 'reserved', '2026-11-03 10:45:00', '2026-11-03 10:45:00'),
  (2, 9, 'reserved', '2026-11-03 10:47:00', '2026-11-03 10:47:00'),
  (3, 9, 'reserved', '2026-11-03 10:48:00', '2026-11-03 10:48:00'),
  (6, 9, 'reserved', '2026-11-03 10:49:00', '2026-11-03 10:49:00'),
  (10, 9, 'reserved', '2026-11-03 10:50:00', '2026-11-03 10:50:00'),
  (13, 9, 'reserved', '2026-11-03 10:51:00', '2026-11-03 10:51:00'),
  (17, 9, 'reserved', '2026-11-03 10:52:00', '2026-11-03 10:52:00'),
  (8, 10, 'reserved', '2026-11-03 10:54:00', '2026-11-03 10:54:00'),
  (18, 10, 'reserved', '2026-11-03 10:55:00', '2026-11-03 10:55:00'),
  (4, 11, 'reserved', '2026-11-03 10:57:00', '2026-11-03 10:57:00'),
  (5, 12, 'reserved', '2026-11-03 10:59:00', '2026-11-03 10:59:00'),
  (9, 12, 'reserved', '2026-11-03 11:00:00', '2026-11-03 11:00:00'),
  (11, 12, 'reserved', '2026-11-03 11:01:00', '2026-11-03 11:01:00'),
  (14, 12, 'reserved', '2026-11-03 11:02:00', '2026-11-03 11:02:00'),
  (1, 13, 'reserved', '2026-11-03 11:04:00', '2026-11-03 11:04:00'),
  (7, 13, 'reserved', '2026-11-03 11:05:00', '2026-11-03 11:05:00'),
  (15, 13, 'reserved', '2026-11-03 11:06:00', '2026-11-03 11:06:00'),
  (2, 14, 'reserved', '2026-11-03 11:08:00', '2026-11-03 11:08:00'),
  (8, 14, 'reserved', '2026-11-03 11:09:00', '2026-11-03 11:09:00'),
  (12, 14, 'reserved', '2026-11-03 11:10:00', '2026-11-03 11:10:00'),
  (16, 14, 'reserved', '2026-11-03 11:11:00', '2026-11-03 11:11:00'),
  (3, 15, 'reserved', '2026-11-03 11:13:00', '2026-11-03 11:13:00'),
  (6, 15, 'reserved', '2026-11-03 11:14:00', '2026-11-03 11:14:00'),
  (11, 15, 'reserved', '2026-11-03 11:15:00', '2026-11-03 11:15:00'),
  (7, 16, 'reserved', '2026-11-03 11:17:00', '2026-11-03 11:17:00'),
  (13, 16, 'reserved', '2026-11-03 11:18:00', '2026-11-03 11:18:00'),
  (17, 16, 'reserved', '2026-11-03 11:19:00', '2026-11-03 11:19:00'),
  (18, 16, 'reserved', '2026-11-03 11:20:00', '2026-11-03 11:20:00'),
  (4, 17, 'reserved', '2026-11-03 11:22:00', '2026-11-03 11:22:00'),
  (10, 17, 'reserved', '2026-11-03 11:23:00', '2026-11-03 11:23:00'),
  (15, 17, 'reserved', '2026-11-03 11:24:00', '2026-11-03 11:24:00'),
  (1, 18, 'reserved', '2026-11-03 11:26:00', '2026-11-03 11:26:00'),
  (8, 18, 'reserved', '2026-11-03 11:27:00', '2026-11-03 11:27:00'),
  (14, 18, 'reserved', '2026-11-03 11:28:00', '2026-11-03 11:28:00'),
  (18, 18, 'reserved', '2026-11-03 11:29:00', '2026-11-03 11:29:00'),
  (5, 19, 'reserved', '2026-11-03 11:31:00', '2026-11-03 11:31:00'),
  (9, 19, 'reserved', '2026-11-03 11:32:00', '2026-11-03 11:32:00'),
  (16, 19, 'reserved', '2026-11-03 11:33:00', '2026-11-03 11:33:00'),
  (2, 20, 'reserved', '2026-11-03 11:35:00', '2026-11-03 11:35:00'),
  (6, 20, 'reserved', '2026-11-03 11:36:00', '2026-11-03 11:36:00'),
  (11, 20, 'reserved', '2026-11-03 11:37:00', '2026-11-03 11:37:00'),
  (12, 20, 'reserved', '2026-11-03 11:38:00', '2026-11-03 11:38:00'),
  (17, 20, 'reserved', '2026-11-03 11:39:00', '2026-11-03 11:39:00');

UPDATE `course` AS c
SET c.`booked_count` = (
  SELECT COUNT(*)
  FROM `appointment` AS a
  WHERE a.`course_id` = c.`id`
    AND a.`status` = 'reserved'
);

SET FOREIGN_KEY_CHECKS = 1;
