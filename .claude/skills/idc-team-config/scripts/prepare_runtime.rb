#!/usr/bin/env ruby
# frozen_string_literal: true

require "optparse"
require "open3"
require "pathname"
require "rbconfig"
require "tempfile"
require "yaml"

harness_root = Pathname.new(__dir__).join("../../../..").expand_path
options = {
  config: harness_root.join("team-config.yaml").to_s,
  output: harness_root.join(".idc/effective-team-config.yaml").to_s
}
OptionParser.new do |parser|
  parser.banner = "Usage: prepare_runtime.rb [--config PATH] [--output PATH]"
  parser.on("--config PATH") { |value| options[:config] = value }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!

config_path = Pathname.new(options[:config]).expand_path
output_path = Pathname.new(options[:output]).expand_path
unless config_path.file?
  puts YAML.dump(
    "runtime_preflight" => {
      "status" => "NEEDS_TEAM_CONFIG",
      "config_ref" => config_path.to_s,
      "reason" => "team-config.yaml is missing; copy team-config.yaml.template and fill it"
    }
  )
  exit 2
end

resolver = Pathname.new(__dir__).join("resolve_team_config.rb")
stdout, stderr, status = Open3.capture3(
  RbConfig.ruby,
  resolver.to_s,
  "--config", config_path.to_s,
  "--output", output_path.to_s,
  chdir: harness_root.to_s
)
unless status.success?
  puts YAML.dump(
    "runtime_preflight" => {
      "status" => "NEEDS_TEAM_CONFIG",
      "config_ref" => config_path.to_s,
      "reason" => stderr.lines.map(&:strip).reject(&:empty?)
    }
  )
  exit status.exitstatus
end

effective = YAML.safe_load(output_path.read, permitted_classes: [], aliases: false) || {}
selector = Pathname.new(__dir__).join("select_capabilities.rb")
context_planner = Pathname.new(__dir__).join("plan_context.rb")
policy_checks = []
policy_errors = []
profiles = effective.dig("lane", "profiles") || {}
capabilities = Array(effective["available_capabilities"]).each_with_object({}) do |capability, index|
  index[capability["id"]] = capability
end

check_selection = lambda do |lane_id, check_id, stage, skill_ids, trigger_signals|
  demand = {
    "capability_demand" => {
      "execution_unit_ref" => "preflight-#{check_id}",
      "selected_stage" => stage,
      "selected_domain" => "general",
      "lane_applicability" => "applicable",
      "selected_lane" => lane_id,
      "execution_profile" => "lane_driven",
      "required_capability_keys" => [],
      "optional_capability_keys" => [],
      "observed_signals" => trigger_signals,
      "contract_refs" => []
    }
  }
  Tempfile.create(["idc-capability-demand", ".yaml"]) do |file|
    file.write(YAML.dump(demand))
    file.flush
    selection_stdout, selection_stderr, selection_status = Open3.capture3(
      RbConfig.ruby,
      selector.to_s,
      "--effective", output_path.to_s,
      "--demand", file.path,
      chdir: harness_root.to_s
    )
    unless selection_status.success?
      policy_errors << "#{check_id}: selector failed: #{selection_stderr.strip} #{selection_stdout.strip}"
      next
    end
    selection = YAML.safe_load(selection_stdout, permitted_classes: [], aliases: false) || {}
    selected_ids = Array(selection.dig("capability_selection_result", "selected")).map { |item| item["capability_id"] }
    unless selected_ids.first(skill_ids.length) == skill_ids
      policy_errors << "#{check_id}: expected ordered prefix #{skill_ids.inspect}, got #{selected_ids.inspect}"
      next
    end
    policy_checks << {
      "id" => check_id,
      "lane" => lane_id,
      "stage" => stage,
      "selected_skill_ids" => selected_ids,
      "status" => "PASS"
    }
  end
end

profiles.each do |lane_id, profile|
  orchestration = profile["orchestration"] || {}
  Array(orchestration["steps"]).each do |step|
    check_selection.call(
      lane_id,
      "#{lane_id}-step-#{step['id']}",
      step["stage"],
      Array(step["skill_ids"]),
      Array(step["trigger_signals"])
    )
  end
  Array(profile.dig("skills", "required")).each do |skill_id|
    capability = capabilities[skill_id]
    next unless capability
    matching_step = Array(orchestration["steps"]).find { |step| Array(step["skill_ids"]).include?(skill_id) }
    stage = matching_step ? matching_step["stage"] : Array(capability["allowed_stages"]).first
    signals = matching_step ? Array(matching_step["trigger_signals"]) : []
    check_selection.call(lane_id, "#{lane_id}-required-#{skill_id}", stage, [skill_id], signals)
  end
end

alignment = effective["alignment"] || {}
alignment_bindings = alignment["bindings"] || {}
alignment_steps = Array(alignment.dig("orchestration", "steps"))
alignment_checks = []
alignment_floor_signals = %w[raw_idea critical_gaps_remain]
covered_alignment_signals = alignment_steps.flat_map { |step| Array(step["trigger_signals"]) }
alignment_floor_missing = alignment_floor_signals.uniq - covered_alignment_signals
alignment_gate_present = alignment_steps.any? { |step| step["stage"] == "alignment_check" }

alignment_steps.each do |step|
  check_id = "alignment-step-#{step['id']}"
  check = {
    "id" => check_id,
    "stage" => step["stage"],
    "skill_ids" => Array(step["skill_ids"]),
    "trigger_signals" => Array(step["trigger_signals"]),
    "status" => "PASS"
  }
  step_errors = []
  if step["id"].to_s.empty? || step["stage"].to_s.empty? || Array(step["skill_ids"]).empty?
    step_errors << "ordered alignment step is missing id/stage/skill_ids"
  end
  Array(step["skill_ids"]).each do |skill_id|
    skill_ref = alignment_bindings.dig(skill_id, "skill_ref").to_s
    if skill_ref.empty?
      step_errors << "skill_id #{skill_id} has no alignment.bindings entry"
      next
    end
    candidate = Pathname.new(skill_ref)
    candidate = harness_root.join(candidate) unless candidate.absolute?
    step_errors << "bound skill_ref does not exist: #{skill_ref}" unless candidate.file?
  end
  unless step_errors.empty?
    check["status"] = "FAIL"
    check["reason"] = step_errors
    policy_errors.concat(step_errors.map { |message| "#{check_id}: #{message}" })
  end
  alignment_checks << check
end

unless alignment_gate_present
  policy_errors << "alignment.orchestration ordered steps must keep the alignment_check gate step"
end
if alignment_floor_missing.any?
  policy_errors << "alignment.orchestration trigger_signals must cover the framework signal floor: #{alignment_floor_missing.join(', ')}"
end

if policy_errors.any?
  puts YAML.dump(
    "runtime_preflight" => {
      "status" => "NEEDS_TEAM_CONFIG",
      "config_ref" => config_path.to_s,
      "effective_config_ref" => output_path.to_s,
      "reason" => policy_errors,
      "alignment_policy_check_count" => alignment_checks.length,
      "alignment_policy_checks" => alignment_checks
    }
  )
  exit 3
end

context_stdout, context_stderr, context_status = Open3.capture3(
  RbConfig.ruby,
  context_planner.to_s,
  "--effective", output_path.to_s,
  "--phase", "bootstrap",
  chdir: harness_root.to_s
)
unless context_status.success?
  puts YAML.dump(
    "runtime_preflight" => {
      "status" => "NEEDS_TEAM_CONFIG",
      "config_ref" => config_path.to_s,
      "effective_config_ref" => output_path.to_s,
      "reason" => "context load planning failed: #{context_stderr.strip} #{context_stdout.strip}"
    }
  )
  exit 4
end
bootstrap_load_plan = YAML.safe_load(context_stdout, permitted_classes: [], aliases: false).fetch("context_load_plan")

puts YAML.dump(
  "runtime_preflight" => {
    "status" => "READY",
    "config_ref" => config_path.to_s,
    "effective_config_ref" => output_path.to_s,
    "source_sha256" => effective["source_sha256"],
    "available_capability_count" => Array(effective["available_capabilities"]).length,
    "registration_audit_status" => effective.dig("registration_audit", "status"),
    "declared_registration_override_count" => Array(effective.dig("registration_audit", "declared_overrides")).length,
    "bootstrap_load_plan" => bootstrap_load_plan,
    "lane_policy_check_count" => policy_checks.length,
    "lane_policy_checks" => policy_checks,
    "alignment_policy_check_count" => alignment_checks.length,
    "alignment_policy_checks" => alignment_checks
  }
)
