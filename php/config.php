<?php
// Database — update these with your Hostinger MySQL credentials
define('DB_HOST', 'localhost');
define('DB_NAME', 'your_database_name');
define('DB_USER', 'your_database_user');
define('DB_PASS', 'your_database_password');

// Anthropic API key
define('ANTHROPIC_API_KEY', getenv('ANTHROPIC_API_KEY') ?: '');

// App settings
define('APP_NAME', 'StatementScrub');
define('UPLOAD_DIR', __DIR__ . '/uploads/');
define('MAX_UPLOAD_MB', 20);
define('SESSION_NAME', 'statementiq_sess');

// Plan limits
define('PLAN_LIMITS', ['free' => 3, 'starter' => 50, 'pro' => 999999]);

session_name(SESSION_NAME);
session_start();
