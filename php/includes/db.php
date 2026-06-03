<?php
function get_db(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO(
            'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
            DB_USER, DB_PASS,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
             PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
        );
    }
    return $pdo;
}

function setup_tables(): void {
    $db = get_db();
    $db->exec("
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) DEFAULT '',
            plan ENUM('free','starter','pro') DEFAULT 'free',
            analyses_used INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS analyses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            filename VARCHAR(255) NOT NULL,
            bank_name VARCHAR(255) DEFAULT '',
            account_holder VARCHAR(255) DEFAULT '',
            statement_period VARCHAR(255) DEFAULT '',
            avg_monthly_deposits DECIMAL(12,2) DEFAULT 0,
            avg_monthly_withdrawals DECIMAL(12,2) DEFAULT 0,
            avg_daily_balance DECIMAL(12,2) DEFAULT 0,
            ending_balance DECIMAL(12,2) DEFAULT 0,
            lowest_balance DECIMAL(12,2) DEFAULT 0,
            nsf_count INT DEFAULT 0,
            overdraft_count INT DEFAULT 0,
            mca_detected TINYINT(1) DEFAULT 0,
            risk_level VARCHAR(20) DEFAULT 'low',
            risk_score INT DEFAULT 0,
            result_json LONGTEXT,
            status ENUM('pending','processing','complete','failed') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ");
}
