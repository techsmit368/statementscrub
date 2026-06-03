<?php
function current_user(): ?array {
    if (empty($_SESSION['user_id'])) return null;
    $db = get_db();
    $stmt = $db->prepare("SELECT * FROM users WHERE id = ?");
    $stmt->execute([$_SESSION['user_id']]);
    return $stmt->fetch() ?: null;
}

function require_login(): array {
    $user = current_user();
    if (!$user) {
        header('Location: /login.php');
        exit;
    }
    return $user;
}

function login_user(array $user): void {
    $_SESSION['user_id'] = $user['id'];
}

function logout_user(): void {
    session_destroy();
}

function register(string $email, string $password, string $full_name): array|string {
    $db = get_db();
    $existing = $db->prepare("SELECT id FROM users WHERE email = ?");
    $existing->execute([$email]);
    if ($existing->fetch()) return "Email already registered.";

    $hash = password_hash($password, PASSWORD_BCRYPT);
    $stmt = $db->prepare("INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)");
    $stmt->execute([$email, $hash, $full_name]);
    return $db->query("SELECT * FROM users WHERE id = " . $db->lastInsertId())->fetch();
}

function attempt_login(string $email, string $password): array|string {
    $db = get_db();
    $stmt = $db->prepare("SELECT * FROM users WHERE email = ?");
    $stmt->execute([$email]);
    $user = $stmt->fetch();
    if (!$user || !password_verify($password, $user['password'])) {
        return "Invalid email or password.";
    }
    return $user;
}

function can_analyze(array $user): bool {
    $limits = PLAN_LIMITS;
    return $user['analyses_used'] < ($limits[$user['plan']] ?? 3);
}
