import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, lstatSync, mkdtempSync, readFileSync, readlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const cli = join(root, "dist", "bin", "idc.js");
const project = mkdtempSync(join(tmpdir(), "idc-installer-"));

function run(...args) {
  return execFileSync("node", [cli, ...args, "--directory", project, "--json"], {
    cwd: root,
    encoding: "utf8",
  });
}

const first = JSON.parse(run("install", "--team", "payments"));
assert.equal(first.status, "READY", JSON.stringify(first, null, 2));
assert.ok(existsSync(join(project, ".claude", "skills", "idc-workflow", "SKILL.md")));
assert.ok(existsSync(join(project, ".claude", "hooks", "verify_plan_confirmation_ask.py")));
assert.equal(lstatSync(join(project, ".cac")).isSymbolicLink(), true);
assert.equal(readlinkSync(join(project, ".cac")), ".claude");
assert.equal(readlinkSync(join(project, "AGENTS.md")), "CLAUDE.md");
assert.match(readFileSync(join(project, "team-config.yaml"), "utf8"), /id: payments/);
assert.ok(existsSync(join(project, ".idc", "effective-team-config.yaml")));
assert.ok(existsSync(join(project, ".idc", "install-manifest.json")));

const settingsPath = join(project, ".claude", "settings.json");
const settings = JSON.parse(readFileSync(settingsPath, "utf8"));
assert.equal(
  settings.hooks.PreToolUse[0].hooks[0].command,
  "python3 .claude/hooks/verify_plan_confirmation_ask.py",
);
settings.permissions = { allow: ["Read"] };
writeFileSync(settingsPath, `${JSON.stringify(settings, null, 2)}\n`);
const second = JSON.parse(run("update"));
assert.equal(second.status, "READY", JSON.stringify(second, null, 2));
assert.deepEqual(JSON.parse(readFileSync(settingsPath, "utf8")).permissions, { allow: ["Read"] });

const managedSkill = join(project, ".claude", "skills", "idc-workflow", "SKILL.md");
writeFileSync(managedSkill, `${readFileSync(managedSkill, "utf8")}\nlocal customization\n`);
const conflict = spawnSync("node", [cli, "update", "--directory", project, "--json"], { cwd: root, encoding: "utf8" });
assert.equal(conflict.status, 2);
assert.equal(JSON.parse(conflict.stdout).status, "CONFLICT");
assert.match(readFileSync(managedSkill, "utf8"), /local customization/);

const doctor = JSON.parse(run("doctor"));
assert.equal(doctor.status, "READY", JSON.stringify(doctor, null, 2));

console.log("通过 npm installer 项目安装、配置保护、升级冲突与 doctor 测试");
