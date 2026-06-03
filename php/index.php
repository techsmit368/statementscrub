<?php
require_once 'config.php';
require_once 'includes/db.php';
require_once 'includes/auth.php';
require_once 'includes/layout.php';
$user = current_user();
render_head('AI Bank Statement Analyzer');
render_nav($user);
?>

<!-- Hero -->
<section class="relative overflow-hidden bg-white">
  <div class="absolute inset-0 bg-gradient-to-br from-sky-50 via-white to-indigo-50 pointer-events-none"></div>
  <div class="relative max-w-7xl mx-auto px-4 sm:px-6 py-20 sm:py-28">
    <div class="max-w-3xl">
      <div class="inline-flex items-center gap-2 bg-sky-50 border border-sky-200 text-sky-700 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
        <span class="w-2 h-2 bg-sky-500 rounded-full" style="animation:pulse 2s infinite"></span>
        AI-Powered — Results in under 30 seconds
      </div>
      <h1 class="text-5xl sm:text-6xl font-black text-slate-900 leading-tight mb-6">
        Bank Statement<br/>Analysis That<br/><span class="gradient-text">Actually Works</span>
      </h1>
      <p class="text-xl text-slate-500 mb-8 max-w-xl leading-relaxed">
        Upload any bank statement PDF. Get instant income verification, MCA detection,
        NSF counts, cash flow trends, and a lender-ready risk report — no manual data entry.
      </p>
      <div class="flex flex-wrap gap-4 mb-12">
        <a href="/register.php" class="bg-gradient-to-r from-sky-500 to-indigo-600 text-white px-8 py-3.5 rounded-xl font-bold text-lg hover:opacity-90 transition shadow-lg">
          Scrub Free — No Card Needed
        </a>
        <a href="#features" class="bg-white border-2 border-slate-200 text-slate-700 px-8 py-3.5 rounded-xl font-bold text-lg hover:border-slate-300 transition">
          See How It Works
        </a>
      </div>
      <div class="flex flex-wrap gap-6 items-center text-sm text-slate-400">
        <span>✓ No credit card</span>
        <span>✓ 3 free reports</span>
        <span>✓ Any bank, any format</span>
        <span>✓ Secure &amp; private</span>
      </div>
    </div>
  </div>
</section>

<!-- Mock report preview -->
<section class="bg-slate-900 py-16">
  <div class="max-w-7xl mx-auto px-4 sm:px-6">
    <div class="text-center mb-10">
      <p class="text-slate-400 text-sm font-medium uppercase tracking-widest mb-2">What you get</p>
      <h2 class="text-3xl font-bold text-white">A complete financial picture in seconds</h2>
    </div>
    <div class="max-w-4xl mx-auto bg-slate-800 rounded-2xl overflow-hidden border border-slate-700 shadow-2xl">
      <div class="bg-slate-700/50 px-6 py-4 flex items-center justify-between border-b border-slate-600">
        <div>
          <div class="font-semibold text-white">John D. — Chase Bank</div>
          <div class="text-slate-400 text-sm">Jan 2024 – Mar 2024 &middot; 3 months</div>
        </div>
        <div class="flex gap-2">
          <span class="bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 px-3 py-1 rounded-lg text-sm font-semibold">RISK: MEDIUM</span>
          <span class="bg-yellow-500 text-slate-900 px-3 py-1 rounded-lg text-sm font-bold">REVIEW</span>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-px bg-slate-700">
        <?php foreach ([
          ['Avg Monthly Deposits','$8,450','text-sky-400'],
          ['Avg Daily Balance','$3,210','text-emerald-400'],
          ['NSF Count','4','text-red-400'],
          ['MCA Loans','Detected','text-orange-400'],
        ] as [$label,$val,$color]): ?>
        <div class="bg-slate-800 px-4 py-4">
          <div class="text-slate-500 text-xs uppercase tracking-wide mb-1"><?= $label ?></div>
          <div class="text-xl font-bold <?= $color ?>"><?= $val ?></div>
        </div>
        <?php endforeach; ?>
      </div>
      <div class="px-6 py-4">
        <div class="text-xs text-sky-400 uppercase tracking-widest mb-1">AI Lender Summary</div>
        <p class="text-slate-300 text-sm leading-relaxed">
          Account shows consistent payroll deposits averaging $8,450/month. 4 NSF events and 1 active
          MCA repayment (~$185/day) detected. Declining balance trend in March warrants additional review.
        </p>
      </div>
    </div>
  </div>
</section>

<!-- How it works -->
<section id="features" class="py-20 bg-white">
  <div class="max-w-7xl mx-auto px-4 sm:px-6">
    <div class="text-center mb-14">
      <p class="text-sky-600 text-sm font-semibold uppercase tracking-widest mb-2">Simple Process</p>
      <h2 class="text-4xl font-bold text-slate-900">Three steps to a full report</h2>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <?php foreach ([
        ['01','Upload PDF','Drag &amp; drop any bank statement PDF — Chase, Wells Fargo, BofA, credit unions, any format.','📄'],
        ['02','AI Scrubs It','AI extracts every transaction, calculates averages, detects MCA loans, NSFs, and risk flags.','🤖'],
        ['03','Get Your Report','Receive a complete lender-ready report with risk score, income verification, and approval recommendation.','📊'],
      ] as [$num,$title,$desc,$icon]): ?>
      <div class="flex items-start gap-4">
        <div class="w-12 h-12 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-xl flex items-center justify-center text-white font-black text-sm shadow-lg flex-shrink-0"><?= $num ?></div>
        <div>
          <div class="text-2xl mb-2"><?= $icon ?></div>
          <h3 class="text-lg font-bold text-slate-900 mb-2"><?= $title ?></h3>
          <p class="text-slate-500 leading-relaxed"><?= $desc ?></p>
        </div>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- Features -->
<section class="py-20 bg-slate-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6">
    <div class="text-center mb-14">
      <h2 class="text-4xl font-bold text-slate-900">Everything a lender needs to know</h2>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <?php foreach ([
        ['💰','Income Verification','Identifies payroll, ACH credits, and recurring deposits with consistency scoring.'],
        ['🚩','NSF &amp; Overdraft Detection','Counts every bounced check, NSF fee, and overdraft event across the statement period.'],
        ['⚡','MCA Loan Detection','Spots merchant cash advance repayments — merchant name, estimated daily payment.'],
        ['📈','Cash Flow Trends','Month-by-month breakdown showing if the account is growing, stable, or declining.'],
        ['🎰','Gambling Flags','Detects casino, betting, and gambling transactions lenders require disclosed.'],
        ['⚖️','Risk Score &amp; Recommendation','0–100 risk score with APPROVE / REVIEW / DECLINE recommendation.'],
      ] as [$icon,$title,$desc]): ?>
      <div class="bg-white rounded-xl p-6 border border-slate-200 card-hover shadow-sm">
        <div class="text-3xl mb-3"><?= $icon ?></div>
        <h3 class="font-bold text-slate-900 mb-2"><?= $title ?></h3>
        <p class="text-slate-500 text-sm leading-relaxed"><?= $desc ?></p>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- Pricing -->
<section class="py-20 bg-white">
  <div class="max-w-7xl mx-auto px-4 sm:px-6">
    <div class="text-center mb-14">
      <p class="text-sky-600 text-sm font-semibold uppercase tracking-widest mb-2">Pricing</p>
      <h2 class="text-4xl font-bold text-slate-900">Start free. Scale as you grow.</h2>
      <p class="text-slate-500 mt-3">No contracts. Cancel anytime.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
      <?php foreach ([
        ['Free','$0','','3 total reports',['3 reports total','Full AI analysis','All detection features','Email support'],false],
        ['Starter','$49','/mo','50 reports/month',['50 reports/month','Full AI analysis','CSV export','Priority support','Report history'],true],
        ['Pro','$149','/mo','Unlimited reports',['Unlimited reports','Full AI analysis','PDF + CSV export','API access','Dedicated support'],false],
      ] as [$plan,$price,$period,$limit,$features,$hot]): ?>
      <div class="relative bg-white rounded-2xl border-2 p-8 card-hover <?= $hot?'border-sky-500 shadow-xl':'border-slate-200 shadow-sm' ?>">
        <?php if ($hot): ?>
        <div class="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-sky-500 to-indigo-600 text-white text-xs px-4 py-1.5 rounded-full font-bold">MOST POPULAR</div>
        <?php endif; ?>
        <div class="text-slate-500 font-semibold mb-2"><?= $plan ?></div>
        <div class="flex items-end gap-1 mb-1">
          <span class="text-4xl font-black text-slate-900"><?= $price ?></span>
          <span class="text-slate-400 mb-1"><?= $period ?></span>
        </div>
        <div class="text-sm text-slate-400 mb-6"><?= $limit ?></div>
        <ul class="space-y-3 mb-8">
          <?php foreach ($features as $f): ?>
          <li class="flex items-center gap-2 text-sm text-slate-600">
            <span class="w-5 h-5 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">✓</span>
            <?= $f ?>
          </li>
          <?php endforeach; ?>
        </ul>
        <a href="/register.php" class="block w-full py-3 rounded-xl text-center font-bold transition <?= $hot?'bg-gradient-to-r from-sky-500 to-indigo-600 text-white hover:opacity-90 shadow-lg':'bg-slate-100 text-slate-700 hover:bg-slate-200' ?>">
          Get Started
        </a>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- CTA -->
<section class="py-20 bg-gradient-to-r from-sky-600 to-indigo-700">
  <div class="max-w-3xl mx-auto px-4 text-center">
    <h2 class="text-4xl font-black text-white mb-4">Ready to scrub your first statement?</h2>
    <p class="text-sky-200 text-lg mb-8">Start free. No credit card. 3 full reports on us.</p>
    <a href="/register.php" class="bg-white text-sky-700 px-10 py-4 rounded-xl font-black text-lg hover:bg-sky-50 transition shadow-2xl inline-block">
      Start Scrubbing Free →
    </a>
  </div>
</section>

<?php render_footer(); ?>
