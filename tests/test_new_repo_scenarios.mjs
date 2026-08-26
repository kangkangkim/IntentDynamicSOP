import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cli = join(root, "dist", "bin", "idc.js");

function freshRepo(label) {
  return mkdtempSync(join(tmpdir(), `idc-${label}-`));
}

function run(project, command, extra = []) {
  const proc = spawnSync(
    "node",
    [cli, command, "--directory", project, "--json", ...extra],
    { cwd: root, encoding: "utf8" },
  );
  let result;
  try {
    result = JSON.parse(proc.stdout);
  } catch {
    throw new Error(`IDC ${command} did not return JSON: ${proc.stdout}\n${proc.stderr}`);
  }
  return { proc, result };
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function write(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

// 1. Greenfield: one command creates both hosts, config, manifest, and runtime.
{
  const project = freshRepo("greenfield");
  const { proc, result } = run(project, "install", ["--team", "checkout"]);
  assert.equal(proc.status, 0);
  assert.equal(result.status, "READY");
  assert.equal(readlinkSync(join(project, ".cac")), ".claude");
  assert.equal(readlinkSync(join(project, "AGENTS.md")), "CLAUDE.md");
  assert.match(readFileSync(join(project, "team-config.yaml"), "utf8"), /id: checkout/);
  assert.ok(existsSync(join(project, ".idc", "effective-team-config.yaml")));
  assert.ok(existsSync(join(project, ".idc", "install-manifest.json")));
}

// 2. Existing config: preserve bytes and resolve a repository-owned team:// Skill.
{
  const project = freshRepo("existing-config");
  const config = `config_version: 1
team: {id: payments, repo_path: .}
domain: {enabled: [general], mode: general}
bindings:
  coding_standard: {skill_ref: 'team://skills/company-standard/SKILL.md'}
`;
  write(join(project, "team-config.yaml"), config);
  write(
    join(project, "skills", "company-standard", "SKILL.md"),
    "---\nname: company-standard\ndescription: Enterprise coding rules.\n---\n\n# Company Standard\n",
  );
  const { proc, result } = run(project, "install");
  assert.equal(proc.status, 0, JSON.stringify(result, null, 2));
  assert.equal(result.status, "READY");
  assert.equal(readFileSync(join(project, "team-config.yaml"), "utf8"), config);
  const effective = readFileSync(join(project, ".idc", "effective-team-config.yaml"), "utf8");
  assert.ok(
    effective.includes(join(project, "skills", "company-standard", "SKILL.md")),
    "team:// Skill ref must resolve inside the target repository",
  );
}

// 3. Config refresh: doctor rebuilds the generated config and updates source SHA.
{
  const project = freshRepo("config-refresh");
  assert.equal(run(project, "install", ["--team", "search"]).proc.status, 0);
  const configPath = join(project, "team-config.yaml");
  const changed = readFileSync(configPath, "utf8").replace("default: lite", "default: fast");
  writeFileSync(configPath, changed);
  const { proc, result } = run(project, "doctor");
  assert.equal(proc.status, 0, JSON.stringify(result, null, 2));
  assert.equal(result.status, "READY");
  const effective = readFileSync(join(project, ".idc", "effective-team-config.yaml"), "utf8");
  assert.match(effective, /default: fast/);
  assert.match(effective, new RegExp(`source_sha256: ${sha256(configPath)}`));
}

// 4. Invalid config: install assets but fail readiness without replacing input.
{
  const project = freshRepo("invalid-config");
  const invalid = "config_version: 999\nteam: {id: broken, repo_path: .}\ndomain: {mode: unknown}\n";
  write(join(project, "team-config.yaml"), invalid);
  const { proc, result } = run(project, "install");
  assert.equal(proc.status, 2);
  assert.equal(result.status, "FAILED");
  assert.equal(readFileSync(join(project, "team-config.yaml"), "utf8"), invalid);
  assert.ok(result.actions.some((item) => item.status === "FAIL" && item.message.includes("runtime preflight failed")));
}

// 5. Host conflicts: never replace an existing .cac directory or AGENTS.md file.
{
  const project = freshRepo("host-conflict");
  write(join(project, ".cac", "keep.txt"), "owned by enterprise agent\n");
  write(join(project, "AGENTS.md"), "enterprise rules\n");
  const { proc, result } = run(project, "install", ["--skip-runtime"]);
  assert.equal(proc.status, 2);
  assert.equal(result.status, "CONFLICT");
  assert.equal(readFileSync(join(project, ".cac", "keep.txt"), "utf8"), "owned by enterprise agent\n");
  assert.equal(readFileSync(join(project, "AGENTS.md"), "utf8"), "enterprise rules\n");
}

// 6. Dry-run: report the plan while leaving a brand-new repository untouched.
{
  const project = freshRepo("dry-run");
  const { proc, result } = run(project, "install", ["--dry-run", "--skip-runtime"]);
  assert.equal(proc.status, 0);
  assert.equal(result.status, "READY");
  assert.equal(existsSync(join(project, ".claude")), false);
  assert.equal(existsSync(join(project, "team-config.yaml")), false);
  assert.equal(existsSync(join(project, ".idc")), false);
}

console.log("通过 6 组全新仓库 team-config 黑盒场景测试");
