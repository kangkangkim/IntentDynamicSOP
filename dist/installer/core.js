import {
  constants,
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readlinkSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { homedir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const SOURCE_CLAUDE = join(PACKAGE_ROOT, ".claude");
const ASSET_GROUPS = ["skills", "agents", "hooks", "workflows"];
const MANAGED_START = "<!-- IDC-HARNESS:START -->";
const MANAGED_END = "<!-- IDC-HARNESS:END -->";

export async function install(options = {}) {
  const targetRoot = options.global ? homedir() : resolve(options.directory || process.cwd());
  const claudeDir = join(targetRoot, ".claude");
  const manifestPath = options.global
    ? join(claudeDir, ".idc-install-manifest.json")
    : join(targetRoot, ".idc", "install-manifest.json");
  const previousManifest = readJson(manifestPath, { files: {} });
  const nextManifest = {
    package: "idc-harness",
    version: "0.1.0",
    scope: options.global ? "global" : "project",
    files: {},
    links: {},
  };
  const result = { command: options.update ? "update" : options.configOnly ? "init" : "install", status: "READY", actions: [], conflicts: [] };

  if (!options.configOnly) {
    for (const group of ASSET_GROUPS) {
      copyManagedTree(join(SOURCE_CLAUDE, group), join(claudeDir, group), group, previousManifest, nextManifest, result, options);
    }
    mergeSettings(join(SOURCE_CLAUDE, "settings.json"), join(claudeDir, "settings.json"), result, options);
    removeStaleManagedFiles(claudeDir, previousManifest, nextManifest, result, options);
  }

  ensureHostLink(join(targetRoot, ".cac"), ".claude", "dir", result, options);
  nextManifest.links[relative(targetRoot, join(targetRoot, ".cac"))] = ".claude";

  if (!options.global) {
    ensureRulesFile(join(targetRoot, "CLAUDE.md"), result, options);
    ensureHostLink(join(targetRoot, "AGENTS.md"), "CLAUDE.md", "file", result, options);
    nextManifest.links["AGENTS.md"] = "CLAUDE.md";
    initializeTeamConfig(targetRoot, options.team, result, options);
    if (!options.skipRuntime && !options.dryRun) runRuntime(targetRoot, result);
  }

  if (!options.dryRun) {
    mkdirSync(dirname(manifestPath), { recursive: true });
    writeFileSync(manifestPath, `${JSON.stringify(nextManifest, null, 2)}\n`);
  }
  if (result.conflicts.length) result.status = "CONFLICT";
  else if (result.actions.some((item) => item.status === "FAIL")) result.status = "FAILED";
  return result;
}

export async function doctor(options = {}) {
  const targetRoot = options.global ? homedir() : resolve(options.directory || process.cwd());
  const result = { command: "doctor", status: "READY", checks: [] };
  checkPath(join(targetRoot, ".claude", "skills", "idc-workflow", "SKILL.md"), "IDC workflow skill is installed", result);
  checkLink(join(targetRoot, ".cac"), ".claude", result);
  if (!options.global) {
    checkLink(join(targetRoot, "AGENTS.md"), "CLAUDE.md", result);
    checkPath(join(targetRoot, "team-config.yaml"), "team-config.yaml exists", result);
    const python = spawnSync("python3", ["-c", "import yaml"], { encoding: "utf8" });
    pushCheck(result, python.status === 0, "python3 and PyYAML are available", python.stderr);
    if (python.status === 0 && existsSync(join(targetRoot, "team-config.yaml"))) runRuntime(targetRoot, result, true);
  }
  if (result.checks.some((item) => item.status === "FAIL")) result.status = "FAILED";
  return result;
}

function copyManagedTree(sourceRoot, targetRoot, group, previousManifest, nextManifest, result, options) {
  if (!existsSync(sourceRoot)) return;
  for (const sourcePath of walkFiles(sourceRoot)) {
    const rel = join(group, relative(sourceRoot, sourcePath));
    const targetPath = join(dirname(targetRoot), rel);
    const sourceHash = hashFile(sourcePath);
    nextManifest.files[rel] = sourceHash;
    if (existsSync(targetPath)) {
      const targetHash = hashFile(targetPath);
      const oldHash = previousManifest.files?.[rel];
      if (targetHash === sourceHash) continue;
      if (!options.force && targetHash !== oldHash) {
        result.conflicts.push(`${relative(resolve(options.directory || process.cwd()), targetPath)} was modified; preserved`);
        continue;
      }
    }
    result.actions.push({ status: existsSync(targetPath) ? "UPDATED" : "CREATED", message: `${rel}${options.dryRun ? " (dry-run)" : ""}` });
    if (!options.dryRun) {
      mkdirSync(dirname(targetPath), { recursive: true });
      cpSync(sourcePath, targetPath, { force: true, mode: constants.COPYFILE_FICLONE });
    }
  }
}

function mergeSettings(sourcePath, targetPath, result, options) {
  const source = readJson(sourcePath, {});
  const target = readJson(targetPath, {});
  const merged = structuredClone(target);
  merged.hooks ||= {};
  for (const [event, matchers] of Object.entries(source.hooks || {})) {
    merged.hooks[event] ||= [];
    for (const matcher of matchers) {
      const signature = JSON.stringify(matcher);
      if (!merged.hooks[event].some((item) => JSON.stringify(item) === signature)) merged.hooks[event].push(matcher);
    }
  }
  if (JSON.stringify(merged) === JSON.stringify(target)) return;
  result.actions.push({ status: existsSync(targetPath) ? "UPDATED" : "CREATED", message: `.claude/settings.json merged${options.dryRun ? " (dry-run)" : ""}` });
  if (!options.dryRun) {
    mkdirSync(dirname(targetPath), { recursive: true });
    writeFileSync(targetPath, `${JSON.stringify(merged, null, 2)}\n`);
  }
}

function removeStaleManagedFiles(claudeDir, previousManifest, nextManifest, result, options) {
  for (const [rel, oldHash] of Object.entries(previousManifest.files || {})) {
    if (rel in nextManifest.files) continue;
    const targetPath = join(claudeDir, rel);
    if (!existsSync(targetPath) || hashFile(targetPath) !== oldHash) continue;
    result.actions.push({ status: "UPDATED", message: `${rel} removed as obsolete${options.dryRun ? " (dry-run)" : ""}` });
    if (!options.dryRun) rmSync(targetPath, { force: true });
  }
}

function ensureRulesFile(targetPath, result, options) {
  const managedBody = readFileSync(join(PACKAGE_ROOT, "CLAUDE.md"), "utf8").trim();
  const block = `${MANAGED_START}\n${managedBody}\n${MANAGED_END}`;
  let current = existsSync(targetPath) ? readFileSync(targetPath, "utf8") : "";
  if (current.includes(MANAGED_START) && current.includes(MANAGED_END)) {
    const expression = new RegExp(`${escapeRegExp(MANAGED_START)}[\\s\\S]*?${escapeRegExp(MANAGED_END)}`);
    const updated = current.replace(expression, block);
    if (updated === current) return;
    current = updated;
  } else {
    current = `${current.trim()}${current.trim() ? "\n\n" : ""}${block}\n`;
  }
  result.actions.push({ status: existsSync(targetPath) ? "UPDATED" : "CREATED", message: `CLAUDE.md managed rules${options.dryRun ? " (dry-run)" : ""}` });
  if (!options.dryRun) writeFileSync(targetPath, current);
}

function initializeTeamConfig(targetRoot, teamId, result, options) {
  const targetPath = join(targetRoot, "team-config.yaml");
  if (existsSync(targetPath)) {
    result.actions.push({ status: "SKIPPED", message: "team-config.yaml preserved" });
    return;
  }
  const normalizedTeam = (teamId || basename(targetRoot)).toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-|-$/g, "") || "team";
  const template = readFileSync(join(PACKAGE_ROOT, "team-config.yaml.template"), "utf8")
    .replace("<TEAM_ID>", normalizedTeam)
    .replace("<REPO_PATH>", ".");
  result.actions.push({ status: "CREATED", message: `team-config.yaml initialized for ${normalizedTeam}${options.dryRun ? " (dry-run)" : ""}` });
  if (!options.dryRun) writeFileSync(targetPath, template);
}

function ensureHostLink(linkPath, target, type, result, options) {
  if (existsSync(linkPath) || isDanglingLink(linkPath)) {
    const stat = lstatSync(linkPath);
    if (stat.isSymbolicLink() && readlinkSync(linkPath) === target) return;
    if (!options.force) {
      result.conflicts.push(`${linkPath} exists and is not the expected link to ${target}`);
      return;
    }
    if (!options.dryRun) rmSync(linkPath, { recursive: stat.isDirectory(), force: true });
  }
  result.actions.push({ status: "CREATED", message: `${basename(linkPath)} -> ${target}${options.dryRun ? " (dry-run)" : ""}` });
  if (!options.dryRun) symlinkSync(target, linkPath, process.platform === "win32" && type === "dir" ? "junction" : type);
}

function runRuntime(targetRoot, result, asCheck = false) {
  const script = join(targetRoot, ".claude", "skills", "idc-team-config", "scripts", "prepare_runtime.py");
  const proc = spawnSync("python3", [script, "--config", join(targetRoot, "team-config.yaml"), "--output", join(targetRoot, ".idc", "effective-team-config.yaml")], { cwd: targetRoot, encoding: "utf8" });
  const message = proc.status === 0 ? "runtime preflight READY" : `runtime preflight failed: ${(proc.stderr || proc.stdout || "unknown error").trim()}`;
  if (asCheck) pushCheck(result, proc.status === 0, message);
  else result.actions.push({ status: proc.status === 0 ? "UPDATED" : "FAIL", message });
}

function checkPath(path, message, result) {
  pushCheck(result, existsSync(path), message);
}

function checkLink(linkPath, expected, result) {
  const ok = (existsSync(linkPath) || isDanglingLink(linkPath)) && lstatSync(linkPath).isSymbolicLink() && readlinkSync(linkPath) === expected;
  pushCheck(result, ok, `${basename(linkPath)} points to ${expected}`);
}

function pushCheck(result, ok, message, detail = "") {
  result.checks.push({ status: ok ? "PASS" : "FAIL", message: `${message}${!ok && detail ? `: ${detail.trim()}` : ""}` });
}

function walkFiles(root) {
  const output = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) output.push(...walkFiles(path));
    else if (entry.isFile()) output.push(path);
  }
  return output;
}

function readJson(path, fallback) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return structuredClone(fallback);
  }
}

function hashFile(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function isDanglingLink(path) {
  try {
    return lstatSync(path).isSymbolicLink();
  } catch {
    return false;
  }
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
