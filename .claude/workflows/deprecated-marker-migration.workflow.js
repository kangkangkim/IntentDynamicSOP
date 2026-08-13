// Official Dynamic Workflow — Deprecated Marker Migration
// 触发: CI / release pipeline hook (每个 release 复跑)
// 循环: repeat fix->verify, 双重停止 (N=5 总轮 或 K=2 连续无新增 failure)
// 基线: 脚本固定复用, 上次结果作只读 baseline 对照 (args.baseline)
// 复跑: 同脚本 + resumeFromRunId 命中缓存; 或 args.baseline 传上次结果做增量对照
//
// args (可选, 全部有安全默认):
//   mdGlob       默认 '**/*.md'
//   cfgGlob      默认 '**/*.{yml,yaml,json,toml,ini}'
//   scanBatch    发现阶段每 agent 扫描文件数, 默认 10
//   fixBatch     修复阶段每 agent 处理文件数, 默认 5 (控制 agent 数与隔离成本)
//   maxRounds    N, 默认 5
//   dryRounds    K, 默认 2
//   baseline     { runId, findings:[{file, markers:[]}] } 上次结果, 只读对照

export const meta = {
  name: 'deprecated-marker-migration',
  description: 'Scan 80 Markdown + 40 config files for deprecated markers; per-batch fix->verify repeat-until-pass (dual stop N=5/K=2); dedup/merge/sort + baseline diff; rerun per release',
  phases: [
    { title: 'Discover', detail: 'enumerate files, fan-out scan batches for deprecated markers' },
    { title: 'Fix+Verify', detail: 'per-batch fix->verify, round-level repeat loop, dual stop' },
    { title: 'Collect', detail: 'barrier: dedup -> merge -> sort -> baseline diff (inline JS)' },
    { title: 'Report', detail: 'completion evidence summary' },
  ],
}

const FILE_LIST_SCHEMA = {
  type: 'object',
  properties: {
    paths: { type: 'array', items: { type: 'string' } },
    total: { type: 'integer' },
  },
  required: ['paths', 'total'],
}

const MARKER_SCHEMA = {
  type: 'object',
  properties: {
    files: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          markers: { type: 'array', items: { type: 'string' } },
        },
        required: ['file', 'markers'],
      },
    },
  },
  required: ['files'],
}

const FIXVERIFY_SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          verdict: { type: 'string', enum: ['pass', 'fail'] },
          fix_suggestion: { type: 'string' },
          remaining_markers: { type: 'array', items: { type: 'string' } },
        },
        required: ['file', 'verdict', 'fix_suggestion', 'remaining_markers'],
      },
    },
  },
  required: ['results'],
}

const REPORT_SCHEMA = {
  type: 'object',
  properties: {
    completion_summary: { type: 'string' },
    stop_reason: { type: 'string', enum: ['all_pass', 'max_rounds', 'converged_dry', 'no_markers'] },
    total_markers: { type: 'integer' },
    fixed: { type: 'integer' },
    still_failing: { type: 'integer' },
    new_vs_baseline: { type: 'integer' },
    escalated: { type: 'boolean' },
  },
  required: ['completion_summary', 'stop_reason', 'total_markers', 'fixed', 'still_failing'],
}

function chunk(arr, size) {
  const out = []
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size))
  return out
}

// ---------- Phase 1: Discover ----------
phase('Discover')
const cfg = args || {}
const mdGlob = cfg.mdGlob || '**/*.md'
const cfgGlob = cfg.cfgGlob || '**/*.{yml,yaml,json,toml,ini}'
const scanBatch = cfg.scanBatch || 10
const fixBatch = cfg.fixBatch || 5
const maxRounds = cfg.maxRounds || 5
const dryRounds = cfg.dryRounds || 2
const baseline = cfg.baseline || null

const enumerated = await agent(
  `Enumerate files matching these globs: Markdown ${mdGlob} and config ${cfgGlob}. ` +
  `Exclude node_modules, .git, dist, build, vendor. Return sorted absolute paths and total count. Do NOT scan contents.`,
  { schema: FILE_LIST_SCHEMA, label: 'enumerate-files' }
)
const allFiles = enumerated.paths
log(`enumerated ${allFiles.length} files`)

const scanBatches = chunk(allFiles, scanBatch)
const discoveries = (await parallel(
  scanBatches.map((b, i) => () =>
    agent(
      `Scan these files for deprecated markers (e.g. "deprecated", "DEPRECATED", "@deprecated", "TODO: remove", version-gated flags, legacy aliases). ` +
      `Files:\n${b.join('\n')}\n` +
      `Return per-file list of marker strings found. Empty markers array if none.`,
      { schema: MARKER_SCHEMA, phase: 'Discover', label: `scan:${i}` }
    )
  )
)).filter(Boolean)

const withMarkers = discoveries.flatMap(d => d.files).filter(f => f.markers && f.markers.length)
log(`discovered ${withMarkers.length} files with deprecated markers`)

if (withMarkers.length === 0) {
  phase('Report')
  const report = await agent(
    'No deprecated markers found in any file. Produce a completion summary noting zero markers and stop_reason=no_markers.',
    { schema: REPORT_SCHEMA, phase: 'Report', label: 'report' }
  )
  return { report, withMarkers: [], allResults: [] }
}

// ---------- Phase 2: Fix+Verify (round-level repeat loop) ----------
phase('Fix+Verify')
let failing = withMarkers.map(f => ({ file: f.file, markers: f.markers.slice() }))
let prevFailingKeys = new Set(failing.map(f => f.file))
let dry = 0
let round = 0
const allResults = []

while (round < maxRounds && failing.length > 0 && dry < dryRounds) {
  round++
  const batches = chunk(failing, fixBatch)
  const roundResults = (await parallel(
    batches.map((b, i) => () =>
      agent(
        `Round ${round}. For each file below: (1) read it, (2) generate a LOCAL fix suggestion for its deprecated markers ` +
        `(do not rewrite the whole file, only the minimal change), (3) run a placeholder verification ` +
        `(grep that the marker is gone / replaced after the suggested change), (4) report per-file verdict.\n` +
        `Files + their current markers:\n${b.map(f => `- ${f.file}: ${JSON.stringify(f.markers)}`).join('\n')}\n` +
        `Return one result per file. verdict=pass if the suggested change removes the marker; fail if marker remains or new issue introduced. ` +
        `remaining_markers = markers still present after the fix.`,
        { schema: FIXVERIFY_SCHEMA, phase: 'Fix+Verify', label: `fix:round${round}:${i}` }
      )
    )
  )).filter(Boolean)

  const flat = roundResults.flatMap(r => r.results)
  allResults.push({ round, results: flat })

  const stillFailing = flat.filter(r => r.verdict === 'fail')
  const stillFailingKeys = new Set(stillFailing.map(r => r.file))
  const newFailures = flat.filter(r => r.verdict === 'fail' && !prevFailingKeys.has(r.file))

  if (newFailures.length === 0) { dry++ } else { dry = 0 }
  prevFailingKeys = stillFailingKeys
  failing = stillFailing.map(r => ({ file: r.file, markers: r.remaining_markers.slice() }))

  log(`round ${round}: ${flat.length - stillFailing.length} pass, ${stillFailing.length} still failing, new=${newFailures.length}, dry=${dry}/${dryRounds}`)
}

const stopReason =
  round >= maxRounds ? 'max_rounds'
  : failing.length === 0 ? 'all_pass'
  : 'converged_dry'

// ---------- Phase 3: Collect (inline: dedup -> merge -> sort -> baseline diff) ----------
phase('Collect')
const finalState = new Map()
for (const r of allResults) {
  for (const f of r.results) finalState.set(f.file, f) // last appearance wins
}
const merged = Array.from(finalState.values()).map(f => ({
  file: f.file,
  fixed: f.verdict === 'pass',
  fix_suggestion: f.fix_suggestion,
  remaining_markers: f.remaining_markers,
}))
merged.sort((a, b) => a.file.localeCompare(b.file))

const baselineKeys = baseline && baseline.findings ? new Set(baseline.findings.map(f => f.file)) : new Set()
const newVsBaseline = merged.filter(f => !baselineKeys.has(f.file)).length

log(`collected ${merged.length} files: ${merged.filter(m => m.fixed).length} fixed, ${merged.filter(m => !m.fixed).length} still failing, ${newVsBaseline} new vs baseline`)

// ---------- Phase 4: Report ----------
phase('Report')
const report = await agent(
  `Produce a release-ready completion summary. Stop reason: ${stopReason} (rounds=${round}, dry=${dry}/${dryRounds}). ` +
  `Files processed: ${merged.length}. Fixed: ${merged.filter(m => m.fixed).length}. Still failing: ${merged.filter(m => !m.fixed).length}. ` +
  `New vs baseline: ${newVsBaseline}. ` +
  `If still_failing > 0 or stop_reason=max_rounds, set escalated=true (triggers escalation policy: repeated_fix_failure / completion_gate_cannot_be_satisfied). ` +
  `Summarize in 3-5 sentences; do not dump full file lists.`,
  { schema: REPORT_SCHEMA, phase: 'Report', label: 'report' }
)

return {
  report,
  stopReason,
  roundsRun: round,
  dryStreak: dry,
  merged,            // 供下次 release 作 baseline (写回 args.baseline)
  newVsBaseline,
}
