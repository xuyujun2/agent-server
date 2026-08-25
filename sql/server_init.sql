SET NAMES utf8mb4;

DROP TABLE IF EXISTS `returns`;
DROP TABLE IF EXISTS `orders`;

CREATE TABLE `orders` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `order_no` VARCHAR(50) UNIQUE NOT NULL,
    `user_id` VARCHAR(50) NOT NULL,
    `product_name` VARCHAR(100),
    `product_price` DECIMAL(10, 2),
    `status` VARCHAR(20) DEFAULT '待支付',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `returns` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `order_no` VARCHAR(50) NOT NULL,
    `user_id` VARCHAR(50) NOT NULL,
    `reason` VARCHAR(500),
    `status` VARCHAR(20) DEFAULT '待审核',
    `pickup_code` VARCHAR(50),
    `logistics_order_no` VARCHAR(50),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `orders` (`order_no`, `user_id`, `product_name`, `product_price`, `status`) VALUES
('ORD20260805001', 'user_001', 'iPhone 15 Pro Max', 8999.00, '已支付'),
('ORD20260805002', 'user_001', 'AirPods Pro 2', 1899.00, '已发货'),
('ORD20260805003', 'user_002', 'MacBook Pro 14', 16999.00, '已签收'),
('ORD20260805004', 'user_003', 'iPad Air', 4799.00, '已完成'),
('ORD20260805005', 'user_001', 'Apple Watch', 3199.00, '待支付');
