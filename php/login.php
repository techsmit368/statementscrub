<?php
require_once 'config.php';
require_once 'includes/db.php';
require_once 'includes/auth.php';
require_once 'includes/layout.php';

if (current_user()) { header('Location: /dashboard.php'); exit; }

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $result = attempt_login(trim($_POST['email'] ?? ''), $_POST['password'] ?? '');
    if (is_string($result)) {
        $error = $result;
    } else {
        login_user($result);
        header('Location: /dashboard.php');
        exit;
    }
}

render_head('Login');
render_nav(null);
?>
<div class="min-h-[80vh] flex items-center justify-center px-4 py-12">
  <div class="w-full max-w-md">
    <div class="text-center mb-8">
      <div class="w-14 h-14 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
        <span class="text-white font-black text-xl">S</span>
      </div>
      <h1 class="text-2xl font-bold text-slate-900">Welcome back</h1>
      <p class="text-slate-400 mt-1">Sign in to your StatementScrub account</p>
    </div>
    <?php if ($error): ?>
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-5 text-sm">⚠️ <?= htmlspecialchars($error) ?></div>
    <?php endif; ?>
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
      <form method="POST" class="space-y-4">
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1.5">Email</label>
          <input type="email" name="email" required placeholder="you@company.com"
            class="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"/>
        </div>
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1.5">Password</label>
          <input type="password" name="password" required placeholder="••••••••"
            class="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"/>
        </div>
        <button type="submit" class="w-full bg-gradient-to-r from-sky-500 to-indigo-600 text-white py-3 rounded-xl font-bold hover:opacity-90 shadow-md mt-2">
          Sign In
        </button>
      </form>
    </div>
    <p class="text-center text-sm text-slate-400 mt-6">
      Don't have an account? <a href="/register.php" class="text-sky-600 font-semibold hover:underline">Create one free</a>
    </p>
  </div>
</div>
<?php render_footer(); ?>
