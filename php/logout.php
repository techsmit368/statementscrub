<?php
require_once 'config.php';
require_once 'includes/auth.php';
logout_user();
header('Location: /index.php');
exit;
