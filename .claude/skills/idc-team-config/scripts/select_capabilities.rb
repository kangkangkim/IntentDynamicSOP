#!/usr/bin/env ruby
# frozen_string_literal: true

require "optparse"
require "pathname"
require "yaml"
require_relative "compat_ruby21"

options = {}
OptionParser.new do |parser|
  parser.banner = "Usage: select_capabilities.rb --effective PATH --demand PATH [--output PATH]"
  parser.on("--effective PATH") { |value| options[:effective] = value }
  parser.on("--demand PATH") { |value| options[:demand] = value }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!

abort "ERROR: --effective and --demand are required" unless options[:effective] && options[:demand]

def load_yaml(path)
  IDCRubyCompat.safe_yaml_load(Pathname.new(path).expand_path.read) || {}
rescue Errno::ENOENT, Psych::Exception => e
  abort "ERROR: #{e.message}"
end

effective = load_yaml(options[:effective])
demand_doc = load_yaml(options[:demand])
demand = demand_doc["capability_demand"] || demand_doc

stage = demand["selected_stage"]
lane_applicability = demand["lane_applicability"]
lane = demand["selected_lane"]
profile = demand["execution_profile"]
required_keys = Array(demand["required_capability_keys"])
optional_keys = Array(demand["optional_capability_keys"])
signals = Array(demand["observed_signals"])
available = Array(effective["available_capabilities"])

profiles = effective.dig("capability_selection", "lane_profiles") || {}
budget = if lane_applicability == "applicable"
           profiles.dig(lane, "max_optional_skills")
         else
           effective.dig("capability_selection", "d3a_profile", "max_optional_skills")
         end

lane_profile = lane_applicability == "applicable" ? (effective.dig("lane", "profiles", lane) || {}) : {}
skill_policy = lane_profile["skills"] || {}
allowed_skill_ids = Array(skill_policy["allow"])
denied_skill_ids = Array(skill_policy["deny"])
configured_required_ids = Array(skill_policy["required"])
orchestration = lane_profile["orchestration"] || {}
orchestration_mode = lane_applicability == "applicable" ? (orchestration["mode"] || "autonomous") : "execution_profile"
orchestration_steps = Array(orchestration["steps"])
capability_signals = available.flat_map { |capability| Array(capability["trigger_signals"]) }
step_signals = lane_applicability == "applicable" ? orchestration_steps.flat_map { |step| Array(step["trigger_signals"]) } : []
known_signals = (capability_signals + step_signals).uniq
unknown_signals = signals - known_signals

unless unknown_signals.empty?
  result = {
    "capability_selection_result" => {
      "execution_unit_ref" => demand["execution_unit_ref"],
      "selected_domain" => demand["selected_domain"],
      "selected_stage" => stage,
      "strategy" => "autonomous_minimal_sufficient",
      "orchestration" => {
        "mode" => orchestration_mode,
        "matched_step_ids" => [],
        "configured_skill_ids" => []
      },
      "selected" => [],
      "skipped" => [],
      "unresolved_required_capabilities" => Array(required_keys),
      "unresolved_configured_skill_ids" => [],
      "status" => "NEEDS_SIGNAL_MAPPING",
      "unknown_signals" => unknown_signals,
      "known_signals_count" => known_signals.length
    }
  }
  output = YAML.dump(result)
  if options[:output]
    Pathname.new(options[:output]).expand_path.write(output)
  else
    puts output
  end
  warn "NEEDS_SIGNAL_MAPPING: unknown observed_signals: #{unknown_signals.join(', ')}; not declared by any capability.trigger_signals or lane step.trigger_signals"
  exit 1
end

matching_steps = orchestration_steps.select do |step|
  next false unless step.is_a?(Hash) && step["stage"] == stage
  required_signals = Array(step["trigger_signals"])
  (required_signals - signals).empty?
end
step_skill_ids = matching_steps.flat_map { |step| Array(step["skill_ids"]) }.uniq
orchestration_missing = lane_applicability == "applicable" && orchestration_mode == "ordered" && matching_steps.empty?

available_by_id = available.each_with_object({}) { |capability, index| index[capability["id"]] = capability }
configured_required_for_stage = configured_required_ids.select do |skill_id|
  capability = available_by_id[skill_id]
  capability && Array(capability["allowed_stages"]).include?(stage)
end
forced_skill_ids = (step_skill_ids + configured_required_for_stage).uniq

selected = []
skipped = []
eligible = []

available.each do |capability|
  id = capability["id"]
  unless Array(capability["allowed_stages"]).include?(stage)
    skipped << { "capability_id" => id, "reason" => "stage_mismatch" }
    next
  end

  if lane_applicability == "applicable"
    unless Array(capability["eligible_lanes"]).include?(lane)
      skipped << { "capability_id" => id, "reason" => "lane_ineligible" }
      next
    end
    if denied_skill_ids.include?(id)
      skipped << { "capability_id" => id, "reason" => "team_lane_denied" }
      next
    end
    if allowed_skill_ids.any? && !allowed_skill_ids.include?(id)
      skipped << { "capability_id" => id, "reason" => "team_lane_not_allowed" }
      next
    end
    if orchestration_mode == "ordered" && !step_skill_ids.include?(id)
      skipped << { "capability_id" => id, "reason" => "orchestration_step_excluded" }
      next
    end
  else
    declared_profiles = Array(capability["execution_profiles"])
    unless declared_profiles.empty? || declared_profiles.include?(profile)
      skipped << { "capability_id" => id, "reason" => "profile_ineligible" }
      next
    end
  end

  keys = Array(capability["capability_keys"])
  required_coverage = keys & required_keys
  optional_coverage = keys & optional_keys
  signal_coverage = Array(capability["trigger_signals"]) & signals
  forced_by_config = forced_skill_ids.include?(id)
  if !forced_by_config && required_coverage.empty? && optional_coverage.empty? && signal_coverage.empty?
    skipped << { "capability_id" => id, "reason" => "signal_missing" }
    next
  end
  eligible << capability.merge(
    "required_coverage" => required_coverage,
    "optional_coverage" => optional_coverage,
    "signal_coverage" => signal_coverage,
    "forced_by_config" => forced_by_config
  )
end

superseded_ids = eligible.flat_map { |capability| Array(capability["supersedes"]) }.uniq
if superseded_ids.any?
  eligible.reject! do |capability|
    next false unless superseded_ids.include?(capability["id"])
    skipped << { "capability_id" => capability["id"], "reason" => "superseded" }
    true
  end
end

unresolved_configured = []
forced_skill_ids.each do |skill_id|
  candidate = eligible.find { |item| item["id"] == skill_id }
  if candidate
    source = step_skill_ids.include?(skill_id) ? "orchestration step" : "Lane required skills"
    selected << candidate.merge("requirement" => "configured", "selection_reason" => "selected by #{source}")
  else
    unresolved_configured << skill_id
  end
end

covered_by_config = selected.flat_map { |item| item["required_coverage"] }.uniq
uncovered = required_keys - covered_by_config
until uncovered.empty?
  candidate = eligible.reject { |item| selected.any? { |picked| picked["id"] == item["id"] } }
                      .max_by { |item| (item["required_coverage"] & uncovered).length }
  break unless candidate && (candidate["required_coverage"] & uncovered).any?
  covered = candidate["required_coverage"] & uncovered
  selected << candidate.merge("requirement" => "required", "selection_reason" => "covers required capability keys: #{covered.join(', ')}")
  uncovered -= covered
end

optional_candidates = eligible.reject { |item| selected.any? { |picked| picked["id"] == item["id"] } }
                              .sort_by { |item| -((item["optional_coverage"].length * 2) + item["signal_coverage"].length) }
optional_candidates.each do |candidate|
  if !budget.nil? && selected.count { |item| item["requirement"] == "optional" } >= budget
    skipped << { "capability_id" => candidate["id"], "reason" => "optional_budget_exhausted" }
    next
  end
  reason_parts = []
  reason_parts << "optional keys: #{candidate['optional_coverage'].join(', ')}" if candidate["optional_coverage"].any?
  reason_parts << "signals: #{candidate['signal_coverage'].join(', ')}" if candidate["signal_coverage"].any?
  selected << candidate.merge("requirement" => "optional", "selection_reason" => reason_parts.join("; "))
end

result = {
  "capability_selection_result" => {
    "execution_unit_ref" => demand["execution_unit_ref"],
    "selected_domain" => demand["selected_domain"],
    "selected_stage" => stage,
    "strategy" => "autonomous_minimal_sufficient",
    "orchestration" => {
      "mode" => orchestration_mode,
      "matched_step_ids" => matching_steps.map { |step| step["id"] },
      "configured_skill_ids" => forced_skill_ids
    },
    "selected" => selected.each_with_index.map do |item, index|
      {
        "capability_id" => item["id"],
        "skill_ref" => item["skill_ref"],
        "requirement" => item["requirement"],
        "execution_order" => index + 1,
        "reason" => item["selection_reason"]
      }
    end,
    "skipped" => skipped.uniq,
    "unresolved_required_capabilities" => uncovered,
    "unresolved_configured_skill_ids" => unresolved_configured,
    "status" => if orchestration_missing
                  "NEEDS_ORCHESTRATION_MAPPING"
                elsif unresolved_configured.any?
                  "NEEDS_TEAM_CONFIG"
                elsif uncovered.empty?
                  "READY"
                else
                  "NEEDS_ADAPTER_MAPPING"
                end
  }
}

output = YAML.dump(result)
if options[:output]
  Pathname.new(options[:output]).expand_path.write(output)
else
  puts output
end
exit_code = if orchestration_missing || unresolved_configured.any?
              3
            elsif uncovered.empty?
              0
            else
              2
            end
exit(exit_code)
