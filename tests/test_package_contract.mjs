import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
const settings = JSON.parse(readFileSync(join(root, ".claude", "settings.json"), "utf8"));

assert.ok(packageJson.files.includes(".claude/hooks/"), "npm files whitelist must include hooks");
assert.ok(packageJson.files.includes(".claude/settings.json"), "npm files whitelist must include shared hook settings");
assert.ok(packageJson.files.includes("team-config.yaml.template"), "npm files whitelist must include the v2 team config template");
assert.equal(packageJson.license, "UNLICENSED", "the public skeleton must not imply an open-source license");

const readme = readFileSync(join(root, "README.md"), "utf8");
assert.match(readme, /企业 npm registry/, "README must scope installation to an enterprise registry");
assert.match(readme, /UNLICENSED/, "README must state the private-distribution license posture");
assert.match(readFileSync(join(root, "dist", "installer", "core.js"), "utf8"), /entry\.name === "__pycache__"/, "installer must not manage Python bytecode artifacts");

const commands = Object.values(settings.hooks || {})
  .flatMap((matchers) => matchers)
  .flatMap((matcher) => matcher.hooks || [])
  .filter((hook) => hook.type === "command")
  .map((hook) => hook.command);

assert.ok(commands.length > 0, "shared settings must register at least one command hook");
for (const command of commands) {
  const match = command.match(/(?:python3|node)\s+([^\s]+)/);
  assert.ok(match, `cannot resolve hook command path: ${command}`);
  assert.ok(existsSync(join(root, match[1])), `registered hook script is missing: ${match[1]}`);
}

console.log("通过 npm 包、hook、私有分发说明发布契约测试");
