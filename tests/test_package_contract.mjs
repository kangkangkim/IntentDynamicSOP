import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
const settings = JSON.parse(readFileSync(join(root, ".claude", "settings.json"), "utf8"));

assert.ok(packageJson.files.includes(".claude/hooks/"), "npm files whitelist must include hooks");
assert.ok(packageJson.files.includes(".claude/settings.json"), "npm files whitelist must include shared hook settings");

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

console.log("通过 npm hook 发布契约测试");
