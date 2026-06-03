<?php
function render_head(string $title = 'StatementScrub'): void { ?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title><?= htmlspecialchars($title) ?> — StatementScrub</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    body{font-family:'Inter',sans-serif}
    .gradient-text{background:linear-gradient(135deg,#0ea5e9,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
    .card-hover{transition:all .2s}.card-hover:hover{transform:translateY(-2px);box-shadow:0 20px 40px rgba(0,0,0,.08)}
    .spinner{width:40px;height:40px;border:3px solid #e2e8f0;border-top-color:#0ea5e9;border-radius:50%;animation:spin .8s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    @keyframes slide-up{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
    .animate-slide-up{animation:slide-up .4s ease forwards}
  </style>
</head>
<body class="bg-slate-50 min-h-screen flex flex-col text-slate-800">
<?php }

function render_nav(?array $user): void { ?>
<nav class="bg-white/90 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50 shadow-sm">
  <div class="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
    <a href="/index.php" class="flex items-center gap-2">
      <div class="w-8 h-8 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-lg flex items-center justify-center">
        <span class="text-white font-bold text-sm">S</span>
      </div>
      <span class="text-xl font-bold text-slate-900">Statement<span class="gradient-text">Scrub</span></span>
    </a>
    <div class="flex items-center gap-3 text-sm">
      <?php if ($user): ?>
        <span class="hidden sm:block text-slate-400 text-xs"><?= htmlspecialchars($user['email']) ?></span>
        <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 text-sky-700"><?= strtoupper($user['plan']) ?></span>
        <a href="/dashboard.php" class="text-slate-600 hover:text-sky-600 font-medium">Dashboard</a>
        <a href="/logout.php" class="text-slate-400 hover:text-red-500">Logout</a>
      <?php else: ?>
        <a href="/login.php" class="text-slate-600 hover:text-sky-600 font-medium">Login</a>
        <a href="/register.php" class="bg-gradient-to-r from-sky-500 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold hover:opacity-90 shadow-sm">Get Started Free</a>
      <?php endif; ?>
    </div>
  </div>
</nav>
<?php }

function render_footer(): void { ?>
<footer class="border-t border-slate-200 bg-white mt-auto">
  <div class="max-w-7xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-slate-400">
    <span>© <?= date('Y') ?> StatementScrub — AI-Powered Bank Statement Analysis</span>
    <span>Built for lenders, brokers &amp; consultants</span>
  </div>
</footer>
</body></html>
<?php }
