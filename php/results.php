<?php
require_once 'config.php';
require_once 'includes/db.php';
require_once 'includes/auth.php';
require_once 'includes/layout.php';

$user = require_login();
$id   = (int)($_GET['id'] ?? 0);
$db   = get_db();
$stmt = $db->prepare("SELECT * FROM analyses WHERE id = ? AND user_id = ?");
$stmt->execute([$id, $user['id']]);
$analysis = $stmt->fetch();
if (!$analysis) { header('Location: /dashboard.php'); exit; }

$result    = $analysis['result_json'] ? json_decode($analysis['result_json'], true) : [];
$rf        = $result['red_flags'] ?? [];
$summary   = $result['summary']   ?? [];
$income    = $result['income']    ?? [];
$expenses  = $result['expenses']  ?? [];
$period    = $result['statement_period'] ?? [];
$risk      = $rf['risk_level']    ?? 'low';
$rec       = $result['approval_recommendation'] ?? 'review';

$rec_colors = ['approve'=>'from-green-500 to-emerald-600','review'=>'from-yellow-500 to-orange-500','decline'=>'from-red-500 to-rose-600'];
$risk_badge = ['low'=>'bg-green-100 text-green-700','medium'=>'bg-yellow-100 text-yellow-700','high'=>'bg-orange-100 text-orange-700','critical'=>'bg-red-100 text-red-700'];

render_head('Report: ' . ($analysis['account_holder'] ?: $analysis['filename']));
render_nav($user);
?>
<div class="max-w-5xl mx-auto px-4 sm:px-6 py-10 animate-slide-up">

  <a href="/dashboard.php" class="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-sky-600 mb-6">← Back to Dashboard</a>

  <!-- Header -->
  <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-6">
    <div class="bg-gradient-to-r <?= $rec_colors[$rec] ?? 'from-slate-500 to-slate-600' ?> p-6 text-white">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="text-white/70 text-sm mb-1">
            <?= htmlspecialchars($result['bank_name'] ?? '') ?>
            <?php if ($period['from'] ?? ''): ?> &middot; <?= htmlspecialchars($period['from']) ?> – <?= htmlspecialchars($period['to'] ?? '') ?><?php endif; ?>
            <?php if ($period['months_covered'] ?? 0): ?> &middot; <?= (int)$period['months_covered'] ?> months<?php endif; ?>
          </div>
          <h1 class="text-2xl sm:text-3xl font-black"><?= htmlspecialchars($result['account_holder'] ?? $analysis['filename']) ?></h1>
        </div>
        <div class="flex items-center gap-3 flex-shrink-0">
          <div class="bg-white/20 rounded-xl px-4 py-3 text-center">
            <div class="text-white/70 text-xs uppercase tracking-widest mb-0.5">Risk Score</div>
            <div class="text-3xl font-black"><?= (int)($rf['risk_score'] ?? 0) ?></div>
            <div class="text-xs font-semibold text-white/80"><?= strtoupper($risk) ?></div>
          </div>
          <div class="bg-white/20 rounded-xl px-4 py-3 text-center">
            <div class="text-white/70 text-xs uppercase tracking-widest mb-0.5">Decision</div>
            <div class="text-xl font-black"><?= strtoupper($rec) ?></div>
          </div>
        </div>
      </div>
    </div>
    <?php if ($result['lender_summary'] ?? ''): ?>
    <div class="px-6 py-4 bg-slate-50 border-b border-slate-100">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
          <span class="text-white text-xs font-bold">AI</span>
        </div>
        <div>
          <div class="text-xs font-semibold text-sky-600 uppercase tracking-widest mb-1">AI Lender Summary</div>
          <p class="text-slate-700 leading-relaxed"><?= htmlspecialchars($result['lender_summary']) ?></p>
        </div>
      </div>
    </div>
    <?php endif; ?>
  </div>

  <!-- Metrics -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
    <?php foreach ([
      ['Avg Monthly Deposits',    '$'.number_format($summary['avg_monthly_deposits']??0,0),    'sky'],
      ['Avg Monthly Expenses',    '$'.number_format($summary['avg_monthly_withdrawals']??0,0),  'slate'],
      ['Avg Daily Balance',       '$'.number_format($summary['avg_daily_balance']??0,0),        ($summary['avg_daily_balance']??0)>=0?'green':'red'],
      ['Ending Balance',          '$'.number_format($summary['ending_balance']??0,0),           ($summary['ending_balance']??0)>=0?'green':'red'],
    ] as [$label,$value,$color]): ?>
    <div class="bg-white rounded-xl border border-slate-200 p-5 card-hover shadow-sm">
      <div class="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2"><?= $label ?></div>
      <div class="text-2xl font-black <?= $color==='sky'?'text-sky-600':($color==='green'?'text-emerald-600':($color==='red'?'text-red-600':'text-slate-900')) ?>"><?= $value ?></div>
    </div>
    <?php endforeach; ?>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

    <!-- Income Sources -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="font-bold text-slate-900">💰 Income Sources</h2>
        <span class="text-xs px-2.5 py-1 rounded-full font-medium bg-sky-100 text-sky-700"><?= ucfirst($income['income_consistency'] ?? '') ?></span>
      </div>
      <div class="text-3xl font-black text-slate-900 mb-1">
        $<?= number_format($income['total_avg_monthly_income'] ?? 0, 0) ?><span class="text-lg font-normal text-slate-400">/mo</span>
      </div>
      <div class="text-sm text-slate-400 mb-5">average monthly income</div>
      <?php foreach (($income['sources'] ?? []) as $src): ?>
      <div class="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
        <div>
          <div class="font-medium text-slate-800 text-sm"><?= htmlspecialchars($src['name'] ?? '') ?></div>
          <div class="text-xs text-slate-400"><?= ucfirst($src['type'] ?? '') ?> &middot; <?= htmlspecialchars($src['frequency'] ?? '') ?></div>
        </div>
        <div class="text-sm font-bold text-emerald-600">$<?= number_format($src['avg_monthly_amount'] ?? 0, 0) ?>/mo</div>
      </div>
      <?php endforeach; ?>
    </div>

    <!-- Risk Flags -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <h2 class="font-bold text-slate-900 mb-4">🚩 Risk Flags</h2>
      <div class="space-y-2.5">
        <?php
        $flags = [
          ['NSF / Bounced Checks',     ($rf['nsf_count']??0)>0,                    ($rf['nsf_count']??0).' events',                                '⚡'],
          ['Overdrafts',               ($rf['overdraft_count']??0)>0,              ($rf['overdraft_count']??0).' events',                          '📉'],
          ['Overdraft Fees Total',     ($rf['overdraft_fees_total']??0)>0,         '$'.number_format($rf['overdraft_fees_total']??0,0),             '💸'],
          ['MCA Loans',                $rf['mca_loans_detected']??false,           ($rf['mca_loans_detected']??false)?'Detected':'None found',      '⚠️'],
          ['Gambling Activity',        $rf['gambling_transactions']??false,        ($rf['gambling_transactions']??false)?'$'.number_format($rf['gambling_total']??0,0):'None found','🎰'],
          ['Declining Balance Trend',  $rf['declining_balance_trend']??false,      ($rf['declining_balance_trend']??false)?'Yes':'No',              '📊'],
        ];
        foreach ($flags as [$label,$bad,$val,$icon]): ?>
        <div class="flex items-center gap-3 p-3 rounded-lg <?= $bad?'bg-red-50 border border-red-100':'bg-green-50 border border-green-100' ?>">
          <span class="text-lg flex-shrink-0"><?= $icon ?></span>
          <span class="flex-1 text-sm font-medium <?= $bad?'text-red-800':'text-green-800' ?>"><?= $label ?></span>
          <span class="text-sm font-bold <?= $bad?'text-red-600':'text-green-600' ?>"><?= htmlspecialchars($val) ?></span>
        </div>
        <?php endforeach; ?>
      </div>
    </div>
  </div>

  <!-- Monthly Breakdown -->
  <?php if ($result['monthly_breakdown'] ?? []): ?>
  <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-6">
    <h2 class="font-bold text-slate-900 mb-5">📅 Monthly Breakdown</h2>
    <?php
    $months = $result['monthly_breakdown'];
    $max_val = max(array_merge(array_column($months,'total_deposits'), array_column($months,'total_withdrawals'), [1]));
    ?>
    <div class="flex gap-2 items-end mb-6 h-36">
      <?php foreach ($months as $mo):
        $dep = $mo['total_deposits'] ?? 0;
        $wid = $mo['total_withdrawals'] ?? 0;
        $dh = $max_val > 0 ? round(($dep/$max_val)*100) : 0;
        $wh = $max_val > 0 ? round(($wid/$max_val)*100) : 0;
      ?>
      <div class="flex-1 flex flex-col items-center gap-1">
        <div class="w-full flex gap-0.5 items-end" style="height:100px">
          <div class="flex-1 bg-sky-400 rounded-t-sm" style="height:<?= $dh ?>px"></div>
          <div class="flex-1 bg-rose-300 rounded-t-sm" style="height:<?= $wh ?>px"></div>
        </div>
        <div class="text-xs text-slate-400"><?= substr($mo['month']??'',-5) ?></div>
        <?php if (($mo['nsf_count']??0)>0): ?>
        <div class="text-xs bg-red-100 text-red-600 rounded-full px-1.5 font-bold"><?= $mo['nsf_count'] ?> NSF</div>
        <?php endif; ?>
      </div>
      <?php endforeach; ?>
      <div class="flex flex-col gap-1.5 text-xs text-slate-400 pb-5 flex-shrink-0 ml-2">
        <span class="flex items-center gap-1.5"><span class="w-3 h-3 bg-sky-400 rounded-sm inline-block"></span>Deposits</span>
        <span class="flex items-center gap-1.5"><span class="w-3 h-3 bg-rose-300 rounded-sm inline-block"></span>Withdrawals</span>
      </div>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr class="border-b border-slate-100">
          <th class="text-left text-xs font-semibold text-slate-400 uppercase pb-2">Month</th>
          <th class="text-right text-xs font-semibold text-slate-400 uppercase pb-2">Deposits</th>
          <th class="text-right text-xs font-semibold text-slate-400 uppercase pb-2">Withdrawals</th>
          <th class="text-right text-xs font-semibold text-slate-400 uppercase pb-2">Ending Balance</th>
          <th class="text-right text-xs font-semibold text-slate-400 uppercase pb-2">NSFs</th>
        </tr></thead>
        <tbody class="divide-y divide-slate-50">
          <?php foreach ($months as $mo): ?>
          <tr class="hover:bg-slate-50">
            <td class="py-3 font-semibold text-slate-700"><?= htmlspecialchars($mo['month']??'') ?></td>
            <td class="py-3 text-right font-medium text-sky-600">$<?= number_format($mo['total_deposits']??0,0) ?></td>
            <td class="py-3 text-right text-slate-600">$<?= number_format($mo['total_withdrawals']??0,0) ?></td>
            <td class="py-3 text-right font-semibold <?= ($mo['ending_balance']??0)<0?'text-red-600':'text-slate-900' ?>">$<?= number_format($mo['ending_balance']??0,0) ?></td>
            <td class="py-3 text-right <?= ($mo['nsf_count']??0)>0?'text-red-600 font-bold':'text-slate-300' ?>"><?= ($mo['nsf_count']??0)?:'—' ?></td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
  </div>
  <?php endif; ?>

  <!-- Expense Categories -->
  <?php if ($expenses['categories'] ?? []): ?>
  <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-6">
    <h2 class="font-bold text-slate-900 mb-4">💸 Expense Breakdown</h2>
    <div class="space-y-3">
      <?php
      $cats = $expenses['categories'];
      usort($cats, fn($a,$b) => ($b['avg_monthly_amount']??0) <=> ($a['avg_monthly_amount']??0));
      foreach ($cats as $cat):
        $pct = min((float)($cat['percentage_of_income']??0), 100);
        $bar = $pct>70?'bg-red-400':($pct>40?'bg-yellow-400':'bg-sky-400');
      ?>
      <div>
        <div class="flex justify-between text-sm mb-1.5">
          <span class="text-slate-700 font-medium"><?= htmlspecialchars($cat['category']??'') ?></span>
          <span class="font-bold text-slate-900">$<?= number_format($cat['avg_monthly_amount']??0,0) ?>/mo <span class="text-slate-400 font-normal">(<?= round($pct) ?>%)</span></span>
        </div>
        <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full rounded-full <?= $bar ?>" style="width:<?= $pct ?>%"></div>
        </div>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
  <?php endif; ?>

  <!-- Actions -->
  <div class="flex flex-wrap gap-3 mt-2">
    <a href="/dashboard.php" class="border border-slate-200 text-slate-600 px-5 py-2.5 rounded-lg hover:bg-slate-50 text-sm font-medium">← Dashboard</a>
    <form method="POST" action="/delete.php" onsubmit="return confirm('Delete this report?')">
      <input type="hidden" name="id" value="<?= $analysis['id'] ?>"/>
      <button type="submit" class="border border-red-200 text-red-400 px-5 py-2.5 rounded-lg hover:bg-red-50 text-sm font-medium">Delete</button>
    </form>
  </div>
</div>
<?php render_footer(); ?>
