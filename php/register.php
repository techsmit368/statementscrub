<?php
require_once 'config.php';
require_once 'includes/db.php';
require_once 'includes/auth.php';
require_once 'includes/layout.php';
setup_tables();

if (current_user()) { header('Location: /dashboard.php'); exit; }

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email     = trim($_POST['email'] ?? '');
    $password  = $_POST['password'] ?? '';
    $full_name = trim($_POST['full_name'] ?? '');
    if (!$email || !$password) {
        $error = 'Email and password are required.';
    } elseif (strlen($password) < 8) {
        $error = 'Password must be at least 8 characters.';
    } else {
        $result = register($email, $password, $full_name);
        if (is_string($result)) {
            $error = $result;
        } else {
            login_user($result);
            header('Location: /dashboard.php');
            exit;
        }
    }
}

render_head('Create Account');
render_nav(null);
?>
<div class="min-h-[80vh] flex items-center justify-center px-4 py-12">
  <div class="w-full max-w-md">
    <div class="text-center mb-8">
      <div class="w-14 h-14 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
        <span class="text-white font-black text-xl">S</span>
      </div>
      <h1 class="text-2xl font-bold text-slate-900">Start for free</h1>
      <p class="text-slate-400 mt-1">3 full reports — no credit card required</p>
    </div>
    <?php if ($error): ?>
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-5 text-sm">⚠️ <?= htmlspecialchars($error) ?></div>
    <?php endif; ?>
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
      <form method="POST" class="space-y-4">
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1.5">Full Name</label>
          <input type="text" name="full_name" placeholder="Jane Smith"
            class="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"/>
        </div>
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1.5">Email</label>
          <input type="email" name="email" required placeholder="you@company.com"
            class="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"/>
        </div>
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1.5">Password</label>
          <input type="password" name="password" required minlength="8" placeholder="8+ characters"
            class="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"/>
        </div>
        <button type="submit" class="w-full bg-gradient-to-r from-sky-500 to-indigo-600 text-white py-3 rounded-xl font-bold hover:opacity-90 shadow-md mt-2">
          Create Free Account →
        </button>
      </form>
    </div>
    <div class="mt-6 grid grid-cols-3 gap-3 text-center text-xs text-slate-400">
      <div><span class="text-green-500 text-lg block">✓</span>No credit card</div>
      <div><span class="text-green-500 text-lg block">✓</span>3 free reports</div>
      <div><span class="text-green-500 text-lg block">✓</span>Instant results</div>
    </div>
    <p class="text-center text-sm text-slate-400 mt-6">
      Already have an account? <a href="/login.php" class="text-sky-600 font-semibold hover:underline">Sign in</a>
    </p>
  </div>
</div>
<?php render_footer(); ?>
