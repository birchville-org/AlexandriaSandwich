#!/bin/sh
# n8n -> alexandria_worker bridge (POSIX + node for JSON)
# Usage: n8n_run_job.sh '{"job":"x",...}'
set -eu
if [ $# -gt 0 ] && [ -n "${1:-}" ]; then
  BODY="$1"
else
  BODY="{}"
fi

if command -v node >/dev/null 2>&1; then
  BODY="$BODY" node <<'NODE'
const { spawnSync } = require('child_process');
let body = {};
try { body = JSON.parse(process.env.BODY || '{}'); } catch (e) {
  console.log(JSON.stringify({ ok:false, error: String(e) }));
  process.exit(2);
}
const job = String(body.job || body.job_name || (`job-${process.pid}`));
const lang = String(body.lang || 'deu+eng');
const threshold = String(body.threshold ?? 100);
const limit = Number(body.limit || 0);
const pull = body.pull !== false && body.pull !== 'false' && body.pull !== 0;
const push = body.push !== false && body.push !== 'false' && body.push !== 0;
const noMistral = body.no_mistral === true || body.no_mistral === 'true' || body.no_mistral === 1;
const skipPreprocess = body.skip_preprocess === true || body.skip_preprocess === 'true' || body.skip_preprocess === 1;
const container = String(body.container || process.env.ALEXANDRIA_CONTAINER || 'alexandria_worker');
const scripts = String(body.scripts_path || process.env.ALEXANDRIA_SCRIPTS || '/opt/alexandria/scripts');
const cmd = [
  'docker','exec',
  '-e',`OCR_LANG=${lang}`,
  '-e',`OCR_CONFIDENCE_THRESHOLD=${threshold}`,
];
if (process.env.MISTRAL_API_KEY) {
  cmd.push('-e', `MISTRAL_API_KEY=${process.env.MISTRAL_API_KEY}`);
}
cmd.push(
  container,
  'bash', `${scripts}/run_pipeline.sh`,
  '--job', job,
  '--lang', lang,
  '--threshold', threshold,
);
if (pull) cmd.push('--pull');
if (push) cmd.push('--push');
if (noMistral) cmd.push('--no-mistral');
if (skipPreprocess) cmd.push('--skip-preprocess');
if (limit > 0) cmd.push('--limit', String(limit));
console.error('[n8n_run_job]', cmd.join(' '));
const r = spawnSync(cmd[0], cmd.slice(1), { encoding: 'utf8', maxBuffer: 20*1024*1024 });
if (r.stderr) process.stderr.write(r.stderr);
if (r.stdout) process.stdout.write(r.stdout);
if ((r.status || 0) !== 0 && !(r.stdout || '').includes('{')) {
  process.stdout.write(JSON.stringify({ ok:false, job, error:`docker exec rc=${r.status}`, stderr:(r.stderr||'').slice(-2000) }) + '\n');
  process.exit(r.status || 1);
}
process.exit(0);
NODE
  exit $?
fi

echo "Error: node not found and no fallback" >&2
exit 127
