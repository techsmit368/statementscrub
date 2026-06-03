<?php
require_once 'config.php';
require_once 'includes/db.php';
require_once 'includes/auth.php';
require_once 'includes/layout.php';

$user = require_login();
$db   = get_db();
$stmt = $db->prepare("SELECT * FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT 20");
$stmt->execute([$user['id']]);
$analyses = $stmt->fetchAll();
$error = htmlspecialchars($_GET['error'] ?? '');

render_head('Dashboard');
render_nav($user);
?>
<div class="max-w-5xl mx-auto px-4 sm:px-6 py-10">

  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-slate-900">My Reports</h1>
      <p class="text-slate-400 text-sm mt-0.5">
        <?= (int)$user['analyses_used'] ?> report<?= $user['analyses_used'] != 1 ? 's' : '' ?> used &middot;
        <span class="text-sky-600 font-semibold capitalize"><?= $user['plan'] ?> plan</span>
      </p>
    </div>
  </div>

  <?php if ($error): ?>
  <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6 text-sm">⚠️ <?= $error ?></div>
  <?php endif; ?>

  <!-- Upload Zone -->
  <div id="uploadZone" class="mb-8 bg-white rounded-2xl border-2 border-dashed border-slate-300 hover:border-sky-400 transition-colors">
    <form method="POST" action="/upload.php" enctype="multipart/form-data" id="uploadForm">
      <input type="file" name="file" id="fileInput" accept=".pdf" class="hidden" onchange="onFileSelected(this)"/>
      <label for="fileInput" class="block p-10 text-center cursor-pointer">
        <div class="w-16 h-16 bg-sky-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <div id="uploadIdleState">
          <p class="text-slate-700 font-semibold text-lg mb-1">Drop a bank statement PDF here</p>
          <p class="text-slate-400 text-sm">or click to browse — any bank, any format, up to 20MB</p>
        </div>
        <div id="uploadReadyState" class="hidden">
          <p class="text-sky-600 font-semibold text-lg mb-1" id="selectedFileName"></p>
          <p class="text-slate-400 text-sm">Ready to analyze</p>
        </div>
      </label>
      <div id="analyzeSection" class="hidden px-10 pb-8 text-center">
        <button type="submit" class="bg-gradient-to-r from-sky-500 to-indigo-600 text-white px-10 py-3.5 rounded-xl font-bold text-lg hover:opacity-90 shadow-lg">
          Analyze Statement →
        </button>
      </div>
    </form>
  </div>

  <!-- Loading state -->
  <div id="loadingState" class="hidden mb-8 bg-sky-50 rounded-2xl border border-sky-200 p-10 text-center">
    <div class="spinner mx-auto mb-4"></div>
    <p class="font-semibold text-slate-700 text-lg mb-1">Analyzing your statement…</p>
    <p class="text-slate-400 text-sm">AI is reading transactions, detecting risk flags, building your report</p>
    <p class="text-sky-500 text-sm mt-3 font-medium">This takes 15–30 seconds</p>
  </div>

  <!-- Reports list -->
  <?php if ($analyses): ?>
  <div>
    <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-4">Recent Reports</h2>
    <div class="space-y-3">
      <?php foreach ($analyses as $a):
        $result = $a['result_json'] ? json_decode($a['result_json'], true) : [];
        $risk   = $a['risk_level'] ?? 'low';
        $colors = ['low'=>'bg-green-400','medium'=>'bg-yellow-400','high'=>'bg-orange-400','critical'=>'bg-red-500'];
        $badge  = ['low'=>'bg-green-100 text-green-700','medium'=>'bg-yellow-100 text-yellow-700','high'=>'bg-orange-100 text-orange-700','critical'=>'bg-red-100 text-red-700'];
      ?>
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden card-hover">
        <?php if ($a['status'] === 'complete'): ?>
        <div class="flex items-center justify-between p-5">
          <div class="flex items-center gap-4">
            <div class="w-1 h-12 rounded-full flex-shrink-0 <?= $colors[$risk] ?? 'bg-gray-300' ?>"></div>
            <div>
              <div class="font-semibold text-slate-900"><?= htmlspecialchars($a['account_holder'] ?: $a['filename']) ?></div>
              <div class="text-sm text-slate-400 mt-0.5">
                <?= htmlspecialchars($a['bank_name'] ?: 'Unknown Bank') ?>
                <?php if ($a['statement_period']): ?> &middot; <?= htmlspecialchars($a['statement_period']) ?><?php endif; ?>
                &middot; <?= date('M d, Y', strtotime($a['created_at'])) ?>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-4 sm:gap-6">
            <div class="hidden sm:block text-center">
              <div class="text-lg font-bold text-slate-900">$<?= number_format($a['avg_monthly_deposits'], 0) ?></div>
              <div class="text-xs text-slate-400">Avg/Mo Deposits</div>
            </div>
            <div class="hidden sm:block text-center">
              <div class="text-lg font-bold <?= $a['nsf_count'] > 0 ? 'text-red-500' : 'text-green-500' ?>"><?= (int)$a['nsf_count'] ?></div>
              <div class="text-xs text-slate-400">NSFs</div>
            </div>
            <?php if ($a['mca_detected']): ?>
            <span class="hidden sm:block bg-orange-100 text-orange-700 text-xs font-semibold px-2.5 py-1 rounded-full">MCA</span>
            <?php endif; ?>
            <span class="text-xs font-bold px-2.5 py-1 rounded-full <?= $badge[$risk] ?? 'bg-gray-100 text-gray-700' ?>"><?= strtoupper($risk) ?></span>
            <a href="/results.php?id=<?= $a['id'] ?>" class="bg-sky-50 text-sky-700 hover:bg-sky-100 px-4 py-2 rounded-lg font-semibold text-sm">View Report →</a>
          </div>
        </div>
        <?php elseif ($a['status'] === 'failed'): ?>
        <div class="flex items-center gap-3 p-5">
          <span class="text-2xl">❌</span>
          <div>
            <div class="font-medium text-slate-700"><?= htmlspecialchars($a['filename']) ?></div>
            <div class="text-sm text-red-400">Analysis failed — try re-uploading</div>
          </div>
        </div>
        <?php else: ?>
        <div class="flex items-center gap-3 p-5">
          <div class="w-5 h-5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin"></div>
          <div class="font-medium text-slate-700"><?= htmlspecialchars($a['filename']) ?> — Processing…</div>
        </div>
        <?php endif; ?>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
  <?php else: ?>
  <div class="text-center py-16 text-slate-400">
    <div class="text-5xl mb-4">📭</div>
    <p class="font-medium text-slate-500 mb-1">No reports yet</p>
    <p class="text-sm">Upload your first bank statement above</p>
  </div>
  <?php endif; ?>
</div>

<script>
function onFileSelected(input) {
  if (!input.files || !input.files[0]) return;
  document.getElementById('uploadIdleState').classList.add('hidden');
  document.getElementById('uploadReadyState').classList.remove('hidden');
  document.getElementById('selectedFileName').textContent = input.files[0].name;
  document.getElementById('analyzeSection').classList.remove('hidden');
}
document.getElementById('uploadForm').addEventListener('submit', function(e) {
  if (!document.getElementById('fileInput').files[0]) { e.preventDefault(); return; }
  document.getElementById('uploadZone').classList.add('hidden');
  document.getElementById('loadingState').classList.remove('hidden');
});
</script>
<?php render_footer(); ?>
