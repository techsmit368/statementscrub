<?php
require_once 'config.php';
require_once 'includes/db.php';
require_once 'includes/auth.php';

$user = require_login();
$id   = (int)($_POST['id'] ?? 0);
$db   = get_db();
$db->prepare("DELETE FROM analyses WHERE id = ? AND user_id = ?")->execute([$id, $user['id']]);
header('Location: /dashboard.php');
exit;
