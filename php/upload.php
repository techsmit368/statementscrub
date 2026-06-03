<?php
require_once 'config.php';
require_once 'includes/db.php';
require_once 'includes/auth.php';
require_once 'includes/pdf.php';
require_once 'includes/claude.php';

$user = require_login();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: /dashboard.php');
    exit;
}

if (!can_analyze($user)) {
    header('Location: /dashboard.php?error=' . urlencode('Plan limit reached. Please upgrade.'));
    exit;
}

$file = $_FILES['file'] ?? null;
if (!$file || $file['error'] !== UPLOAD_ERR_OK) {
    header('Location: /dashboard.php?error=' . urlencode('Upload failed. Please try again.'));
    exit;
}

if (strtolower(pathinfo($file['name'], PATHINFO_EXTENSION)) !== 'pdf') {
    header('Location: /dashboard.php?error=' . urlencode('Only PDF files are supported.'));
    exit;
}

if ($file['size'] > MAX_UPLOAD_MB * 1024 * 1024) {
    header('Location: /dashboard.php?error=' . urlencode('File too large. Max ' . MAX_UPLOAD_MB . 'MB.'));
    exit;
}

// Save upload temporarily
$tmp_path = UPLOAD_DIR . uniqid('stmt_', true) . '.pdf';
if (!move_uploaded_file($file['tmp_name'], $tmp_path)) {
    header('Location: /dashboard.php?error=' . urlencode('Could not save uploaded file.'));
    exit;
}

// Create analysis record
$db = get_db();
$stmt = $db->prepare("INSERT INTO analyses (user_id, filename, status) VALUES (?, ?, 'processing')");
$stmt->execute([$user['id'], basename($file['name'])]);
$analysis_id = $db->lastInsertId();

try {
    $raw_text = extract_pdf_text($tmp_path);
    $text     = truncate_text($raw_text);
    $result   = analyze_with_claude($text);

    $summary   = $result['summary']    ?? [];
    $red_flags = $result['red_flags']  ?? [];
    $period    = $result['statement_period'] ?? [];

    $upd = $db->prepare("
        UPDATE analyses SET
            bank_name = ?, account_holder = ?, statement_period = ?,
            avg_monthly_deposits = ?, avg_monthly_withdrawals = ?,
            avg_daily_balance = ?, ending_balance = ?, lowest_balance = ?,
            nsf_count = ?, overdraft_count = ?, mca_detected = ?,
            risk_level = ?, risk_score = ?,
            result_json = ?, status = 'complete'
        WHERE id = ?
    ");
    $upd->execute([
        $result['bank_name']      ?? '',
        $result['account_holder'] ?? '',
        ($period['from'] ?? '') . ' to ' . ($period['to'] ?? ''),
        $summary['avg_monthly_deposits']    ?? 0,
        $summary['avg_monthly_withdrawals'] ?? 0,
        $summary['avg_daily_balance']       ?? 0,
        $summary['ending_balance']          ?? 0,
        $summary['lowest_balance']          ?? 0,
        $red_flags['nsf_count']             ?? 0,
        $red_flags['overdraft_count']       ?? 0,
        ($red_flags['mca_loans_detected']   ?? false) ? 1 : 0,
        $red_flags['risk_level']            ?? 'low',
        $red_flags['risk_score']            ?? 0,
        json_encode($result),
        $analysis_id,
    ]);

    $db->prepare("UPDATE users SET analyses_used = analyses_used + 1 WHERE id = ?")->execute([$user['id']]);

} catch (Exception $e) {
    $db->prepare("UPDATE analyses SET status = 'failed' WHERE id = ?")->execute([$analysis_id]);
    @unlink($tmp_path);
    header('Location: /dashboard.php?error=' . urlencode('Analysis failed: ' . $e->getMessage()));
    exit;
}

@unlink($tmp_path);
header('Location: /results.php?id=' . $analysis_id);
exit;
