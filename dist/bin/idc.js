#!/usr/bin/env node

import { Command } from "commander";
import { doctor, install } from "../installer/core.js";

const program = new Command();

program
  .name("idc")
  .description("Install and manage the Intent-Driven Coding harness")
  .version("0.1.0");

function addTargetOptions(command) {
  return command
    .option("-C, --directory <path>", "target project directory", process.cwd())
    .option("-g, --global", "install reusable assets in the user home directory")
    .option("--dry-run", "show planned changes without writing files")
    .option("--force", "replace conflicting managed files and host links")
    .option("--json", "emit a machine-readable result");
}

addTargetOptions(
  program.command("install").description("install IDC assets and initialize a project")
)
  .option("--team <id>", "team id used when initializing team-config.yaml")
  .option("--skip-runtime", "do not generate .idc/effective-team-config.yaml")
  .action(async (options) => {
    const result = await install(options);
    printResult(result, options.json);
    if (result.status === "CONFLICT" || result.status === "FAILED") process.exitCode = 2;
  });

addTargetOptions(
  program.command("init").description("initialize project config and host links")
)
  .option("--team <id>", "team id used when initializing team-config.yaml")
  .option("--skip-runtime", "do not generate .idc/effective-team-config.yaml")
  .action(async (options) => {
    const result = await install({ ...options, configOnly: true });
    printResult(result, options.json);
    if (result.status === "CONFLICT" || result.status === "FAILED") process.exitCode = 2;
  });

addTargetOptions(
  program.command("update").description("update IDC-managed assets without replacing team-config.yaml")
)
  .option("--skip-runtime", "do not regenerate .idc/effective-team-config.yaml")
  .action(async (options) => {
    const result = await install({ ...options, update: true });
    printResult(result, options.json);
    if (result.status === "CONFLICT" || result.status === "FAILED") process.exitCode = 2;
  });

addTargetOptions(
  program.command("doctor").description("verify links, dependencies, configuration, and runtime readiness")
)
  .action(async (options) => {
    const result = await doctor(options);
    printResult(result, options.json);
    if (result.status !== "READY") process.exitCode = 2;
  });

function printResult(result, jsonOutput) {
  if (jsonOutput) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }
  console.log(`IDC ${result.command}: ${result.status}`);
  for (const item of result.actions || []) console.log(`${symbol(item.status)} ${item.message}`);
  for (const item of result.checks || []) console.log(`${symbol(item.status)} ${item.message}`);
  for (const conflict of result.conflicts || []) console.error(`! ${conflict}`);
}

function symbol(status) {
  if (status === "PASS" || status === "CREATED" || status === "UPDATED") return "✓";
  if (status === "SKIPPED") return "-";
  return "✗";
}

program.parseAsync(process.argv).catch((error) => {
  console.error(`IDC failed: ${error.message}`);
  process.exitCode = 2;
});
