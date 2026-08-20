#!/usr/bin/env ruby
# frozen_string_literal: true

require "fileutils"
require "digest"
require "json"
require "optparse"
require "pathname"
require "yaml"

options = { check: false }
OptionParser.new do |parser|
  parser.banner = "Usage: resolve_team_config.rb --config PATH [--check | --output PATH]"
  parser.on("--config PATH") { |value| options[:config] = value }
  parser.on("--check") { options[:check] = true }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!

abort "ERROR: --config is required" unless options[:config]
abort "ERROR: choose --check or --output" unless options[:check] || options[:output]

config_path = Pathname.new(options[:config]).expand_path
abort "ERROR: config not found: #{config_path}" unless config_path.file?

root_candidates = [Pathname.pwd.expand_path, config_path.dirname]
root_candidates.concat(config_path.dirname.ascend.to_a)
harness_root = root_candidates.find { |path| path.join(".claude/skills/idc-workflow").directory? }
abort "ERROR: cannot locate IDC harness root" unless harness_root

begin
  source_text = config_path.read
  config = YAML.safe_load(source_text, permitted_classes: [], aliases: false)
rescue Psych::Exception => e
  abort "ERROR: invalid YAML: #{e.message}"
end

errors = []
warnings = []

unless config.is_a?(Hash)
  abort "ERROR: root must be a mapping"
end

def value_at(hash, *keys)
  keys.reduce(hash) { |node, key| node.is_a?(Hash) ? node[key] : nil }
end

def dotted_value(hash, path)
  value_at(hash, *path.to_s.split("."))
end

def present?(value)
  !value.nil? && value != "" && value != [] && value != {}
end

def walk_keys(value, path = [], &block)
  case value
  when Hash
    value.each do |key, child|
      yield(path + [key.to_s], key.to_s)
      walk_keys(child, path + [key.to_s], &block)
    end
  when Array
    value.each_with_index { |child, index| walk_keys(child, path + [index.to_s], &block) }
  end
end

def resolve_file_ref(ref, team_root, harness_root)
  value = ref.to_s
  return harness_root.join(value.delete_prefix("harness://")).cleanpath.to_s if value.start_with?("harness://")
  return team_root.join(value.delete_prefix("team://")).cleanpath.to_s if value.start_with?("team://")
  return value if value.match?(%r{^[a-z][a-z0-9+.-]*:}i)

  path = Pathname.new(value)
  return path.cleanpath.to_s if path.absolute?

  team_candidate = team_root.join(path).cleanpath
  harness_candidate = harness_root.join(path).cleanpath
  return team_candidate.to_s if team_candidate.exist?
  return harness_candidate.to_s if harness_candidate.exist?

  team_candidate.to_s
end

def validate_registry(entries, path, errors)
  unless entries.is_a?(Array)
    errors << "#{path} must be a list"
    return
  end
  ids = []
  entries.each_with_index do |entry, index|
    unless entry.is_a?(Hash)
      errors << "#{path}[#{index}] must be a mapping"
      next
    end
    id = entry["id"]
    ref = entry["knowledge_ref"]
    errors << "#{path}[#{index}].id is required" unless present?(id)
    errors << "#{path}[#{index}].knowledge_ref is required" unless present?(ref)
    errors << "#{path}[#{index}].id is duplicated" if present?(id) && ids.include?(id)
    ids << id if present?(id)
  end
end

forbidden_keys = %w[command build_command run_command pass_condition]
walk_keys(config) do |path, key|
  errors << "#{path.join('.')} is forbidden; bind a skill_ref instead" if forbidden_keys.include?(key)
end

errors << "config_version must be 1" unless config["config_version"] == 1
errors << "team.id is required" unless present?(value_at(config, "team", "id"))
errors << "team.repo_path is required" unless present?(value_at(config, "team", "repo_path"))

team_repo_ref = value_at(config, "team", "repo_path")
team_root = if present?(team_repo_ref)
              path = Pathname.new(team_repo_ref.to_s)
              path = harness_root.join(path) unless path.absolute?
              path.cleanpath
            else
              harness_root
            end
errors << "team.repo_path does not exist or is not a directory: #{team_repo_ref}" unless team_root.directory?

mode = value_at(config, "domain", "mode")
errors << "domain.mode must be d3a, general, or custom" unless %w[d3a general custom].include?(mode)

validate_registry(value_at(config, "domain", "d3a", "dt_domains") || [], "domain.d3a.dt_domains", errors)
validate_registry(value_at(config, "general", "components") || [], "general.components", errors)
validate_registry(value_at(config, "general", "test_domains") || [], "general.test_domains", errors)

custom = value_at(config, "domain", "custom") || {}
if mode == "custom"
  errors << "domain.custom.id is required" unless present?(custom["id"])
  errors << "domain.custom.trigger_rules must not be empty" unless present?(custom["trigger_rules"])
  validate_registry(custom["coding_layers"] || [], "domain.custom.coding_layers", errors)
  validate_registry(custom["test_domains"] || [], "domain.custom.test_domains", errors)
  errors << "domain.custom.coding_layers must not be empty" unless present?(custom["coding_layers"])
  errors << "domain.custom.test_domains must not be empty" unless present?(custom["test_domains"])
  %w[workflow_skill_ref planner_skill_ref completion_skill_ref].each do |key|
    errors << "domain.custom.#{key} is required" unless present?(custom[key])
  end
end

lane_policy = custom["lane_policy"] || {}
if mode == "custom"
  policy_mode = lane_policy["mode"]
  errors << "domain.custom.lane_policy.mode is invalid" unless %w[dynamic fixed not_applicable].include?(policy_mode)
  if policy_mode == "fixed" && !%w[fast lite complex].include?(lane_policy["selected_lane"])
    errors << "domain.custom.lane_policy.selected_lane is required for fixed mode"
  end
  if policy_mode != "fixed" && present?(lane_policy["selected_lane"])
    errors << "domain.custom.lane_policy.selected_lane is allowed only for fixed mode"
  end
end

unless config["lane"].is_a?(Hash)
  config["lane"] = {}
end
lane_default = value_at(config, "lane", "default")
if lane_default.nil?
  lane_default = "lite"
  config["lane"]["default"] = lane_default
  warnings << "lane.default is absent; using lite"
end
errors << "lane.default must be fast, lite, or complex" unless %w[fast lite complex].include?(lane_default)

lane_profiles = value_at(config, "lane", "profiles")
if lane_profiles.nil?
  lane_profiles = {}
  warnings << "lane.profiles is absent; using backward-compatible autonomous profiles"
elsif !lane_profiles.is_a?(Hash)
  errors << "lane.profiles must be a mapping"
  lane_profiles = {}
end
%w[fast lite complex].each do |lane_id|
  profile = lane_profiles[lane_id]
  if profile.nil?
    profile = {
      "skills" => { "allow" => [], "deny" => [], "required" => [] },
      "orchestration" => { "mode" => "autonomous", "steps" => [] }
    }
    lane_profiles[lane_id] = profile
  elsif !profile.is_a?(Hash)
    errors << "lane.profiles.#{lane_id} must be a mapping"
    next
  end
  skill_policy = profile["skills"]
  unless skill_policy.is_a?(Hash)
    errors << "lane.profiles.#{lane_id}.skills must be a mapping"
    skill_policy = {}
  end
  %w[allow deny required].each do |key|
    value = skill_policy[key]
    errors << "lane.profiles.#{lane_id}.skills.#{key} must be a list" unless value.is_a?(Array)
    errors << "lane.profiles.#{lane_id}.skills.#{key} must contain unique skill IDs" if value.is_a?(Array) && value.uniq.length != value.length
  end
  allowed = Array(skill_policy["allow"])
  denied = Array(skill_policy["deny"])
  required = Array(skill_policy["required"])
  errors << "lane.profiles.#{lane_id}.skills.required cannot also be denied" if (required & denied).any?
  if allowed.any? && (required - allowed).any?
    errors << "lane.profiles.#{lane_id}.skills.required must be included in allow when allow is non-empty"
  end

  orchestration = profile["orchestration"]
  unless orchestration.is_a?(Hash)
    errors << "lane.profiles.#{lane_id}.orchestration must be a mapping"
    next
  end
  orchestration_mode = orchestration["mode"]
  errors << "lane.profiles.#{lane_id}.orchestration.mode must be autonomous or ordered" unless %w[autonomous ordered].include?(orchestration_mode)
  steps = orchestration["steps"]
  unless steps.is_a?(Array)
    errors << "lane.profiles.#{lane_id}.orchestration.steps must be a list"
    next
  end
  errors << "lane.profiles.#{lane_id}.orchestration.steps must not be empty in ordered mode" if orchestration_mode == "ordered" && steps.empty?
  step_ids = []
  steps.each_with_index do |step, index|
    path = "lane.profiles.#{lane_id}.orchestration.steps[#{index}]"
    unless step.is_a?(Hash)
      errors << "#{path} must be a mapping"
      next
    end
    errors << "#{path}.id is required" unless present?(step["id"])
    errors << "#{path}.id is duplicated" if present?(step["id"]) && step_ids.include?(step["id"])
    step_ids << step["id"] if present?(step["id"])
    errors << "#{path}.stage is required" unless present?(step["stage"])
    errors << "#{path}.skill_ids must not be empty" unless present?(step["skill_ids"])
    errors << "#{path}.skill_ids must be a list" unless step["skill_ids"].is_a?(Array)
    errors << "#{path}.trigger_signals must be a list" unless step["trigger_signals"].is_a?(Array)
  end
end

capability_selection = config["capability_selection"]
if capability_selection.nil?
  capability_selection = {
    "mode" => "autonomous_minimal_sufficient",
    "lane_profiles" => {
      "fast" => { "max_optional_skills" => 1 },
      "lite" => { "max_optional_skills" => 3 },
      "complex" => { "max_optional_skills" => nil }
    },
    "d3a_profile" => { "max_optional_skills" => nil },
    "require_selected_and_skipped_reasons" => true
  }
  config["capability_selection"] = capability_selection
  warnings << "capability_selection is absent; using safe defaults"
end
unless capability_selection["mode"] == "autonomous_minimal_sufficient"
  errors << "capability_selection.mode must be autonomous_minimal_sufficient"
end
unless capability_selection["require_selected_and_skipped_reasons"] == true
  errors << "capability_selection.require_selected_and_skipped_reasons must be true"
end
%w[fast lite complex].each do |lane_id|
  budget = value_at(capability_selection, "lane_profiles", lane_id, "max_optional_skills")
  if !budget.nil? && (!budget.is_a?(Integer) || budget.negative?)
    errors << "capability_selection.lane_profiles.#{lane_id}.max_optional_skills must be null or a non-negative integer"
  end
end
d3a_budget = value_at(capability_selection, "d3a_profile", "max_optional_skills")
if !d3a_budget.nil? && (!d3a_budget.is_a?(Integer) || d3a_budget.negative?)
  errors << "capability_selection.d3a_profile.max_optional_skills must be null or a non-negative integer"
end

bindings = config["bindings"] || {}
unless bindings.is_a?(Hash)
  errors << "bindings must be a mapping"
  bindings = {}
end

extensions = config["adapter_extensions"] || []
unless extensions.is_a?(Array)
  errors << "adapter_extensions must be a list"
  extensions = []
end
extensions.each_with_index do |entry, index|
  path = "adapter_extensions[#{index}]"
  unless entry.is_a?(Hash)
    errors << "#{path} must be a mapping"
    next
  end
  errors << "#{path}.id must start with idc-" unless entry["id"].to_s.start_with?("idc-")
  errors << "#{path}.capability_keys must not be empty" unless present?(entry["capability_keys"])
  errors << "#{path}.allowed_stages must not be empty" unless present?(entry["allowed_stages"])
  errors << "#{path}.skill_ref is required" unless present?(entry["skill_ref"])
  if entry["execution_role"].nil?
    entry["execution_role"] = "atomic_capability"
    warnings << "#{path}.execution_role is absent; using atomic_capability"
  end
  unless %w[atomic_capability verification_capability pre_alignment_capability].include?(entry["execution_role"])
    errors << "#{path}.execution_role cannot own orchestration; use atomic_capability, verification_capability, or pre_alignment_capability"
  end
  %w[composes_with supersedes].each do |key|
    entry[key] = [] if entry[key].nil?
    errors << "#{path}.#{key} must be a list" unless entry[key].is_a?(Array)
  end
  errors << "#{path} cannot both compose with and supersede the same skill" if (Array(entry["composes_with"]) & Array(entry["supersedes"])).any?
  reserved_capability_keys = %w[domain_selection lane_selection contract_gate human_alignment completion_gate workflow_orchestration domain_execution delegation]
  attempted_keys = Array(entry["capability_keys"]) & reserved_capability_keys
  errors << "#{path}.capability_keys contains protected orchestration ownership: #{attempted_keys.join(', ')}" if attempted_keys.any?
  forbidden_ownership = %w[domain_selection lane_selection contract_gate human_alignment completion_gate]
  attempted = forbidden_ownership & Array(entry["may_override"]&.keys)
  errors << "#{path}.may_override cannot contain protected ownership keys: #{attempted.join(', ')}" if attempted.any?
end

skill_refs = []
bindings.each do |name, binding|
  next unless binding.is_a?(Hash) && present?(binding["skill_ref"])
  skill_refs << ["bindings.#{name}.skill_ref", binding, "skill_ref"]
end
%w[workflow_skill_ref planner_skill_ref completion_skill_ref].each do |key|
  skill_refs << ["domain.custom.#{key}", custom, key] if present?(custom[key])
end
extensions.each_with_index do |entry, index|
  skill_refs << ["adapter_extensions[#{index}].skill_ref", entry, "skill_ref"] if entry.is_a?(Hash) && present?(entry["skill_ref"])
end
provider_ref = value_at(config, "knowledge", "repo_context", "provider_skill_ref")
repo_context = value_at(config, "knowledge", "repo_context")
skill_refs << ["knowledge.repo_context.provider_skill_ref", repo_context, "provider_skill_ref"] if present?(provider_ref) && repo_context.is_a?(Hash)

skill_refs.each do |path, owner, key|
  original_ref = owner[key]
  protected_atomic_skills = %w[
    idc-workflow
    idc-general-coding
    idc-d3a-coding
    idc-intent-discovery
    idc-intent-grilling
    idc-intent-alignment
    idc-team-config
    idc-self-optimization
    idc-skill-adapter-router
  ]
  if (path.start_with?("bindings.") || path.start_with?("adapter_extensions[")) && protected_atomic_skills.any? { |name| original_ref.to_s.include?("/#{name}/") }
    errors << "#{path} binds an orchestration/domain Skill as an atomic capability: #{original_ref}"
  end
  if path.start_with?("bindings.") && original_ref.to_s.include?("/idc-brainstorming/") && path != "bindings.brainstorming.skill_ref"
    errors << "#{path} binds idc-brainstorming outside the brainstorming slot"
  end
  resolved_ref = resolve_file_ref(original_ref, team_root, harness_root)
  if resolved_ref.match?(%r{^[a-z][a-z0-9+.-]*:}i)
    owner[key] = resolved_ref
    next
  end
  candidate = Pathname.new(resolved_ref)
  errors << "#{path} does not exist: #{original_ref} (resolved to #{resolved_ref})" unless candidate.file?
  owner[key] = resolved_ref
end

knowledge_refs = []
[
  ["domain.d3a.dt_domains", value_at(config, "domain", "d3a", "dt_domains")],
  ["domain.custom.coding_layers", custom["coding_layers"]],
  ["domain.custom.test_domains", custom["test_domains"]],
  ["general.components", value_at(config, "general", "components")],
  ["general.test_domains", value_at(config, "general", "test_domains")]
].each do |path, entries|
  Array(entries).each_with_index do |entry, index|
    knowledge_refs << ["#{path}[#{index}].knowledge_ref", entry, "knowledge_ref"] if entry.is_a?(Hash) && present?(entry["knowledge_ref"])
  end
end
knowledge = config["knowledge"]
if knowledge.is_a?(Hash)
  %w[architecture_doc_ref feature_docs_root_ref verification_mapping_ref].each do |key|
    knowledge_refs << ["knowledge.#{key}", knowledge, key] if present?(knowledge[key])
  end
  if knowledge["layer_docs"].is_a?(Hash)
    knowledge["layer_docs"].each do |layer, ref|
      knowledge_refs << ["knowledge.layer_docs.#{layer}", knowledge["layer_docs"], layer] if present?(ref)
    end
  end
  if repo_context.is_a?(Hash) && present?(repo_context["policy_ref"])
    knowledge_refs << ["knowledge.repo_context.policy_ref", repo_context, "policy_ref"]
  end
end

knowledge_refs.each do |path, owner, key|
  original_ref = owner[key]
  resolved_ref = resolve_file_ref(original_ref, team_root, harness_root)
  if resolved_ref.match?(%r{^[a-z][a-z0-9+.-]*:}i)
    owner[key] = resolved_ref
    next
  end
  candidate = Pathname.new(resolved_ref)
  errors << "#{path} does not exist: #{original_ref} (resolved to #{resolved_ref})" unless candidate.exist?
  owner[key] = resolved_ref
end

self_optimization = config["self_optimization"]
if self_optimization.nil?
  self_optimization = {
    "mode" => "disabled",
    "event_store_ref" => nil,
    "replay_cases_ref" => nil,
    "team_overlay_ref" => nil,
    "promotion_requires_human_alignment" => true,
    "auto_modify_core" => false
  }
  config["self_optimization"] = self_optimization
  warnings << "self_optimization is absent; using disabled safe defaults"
end
optimization_mode = self_optimization["mode"]
unless %w[disabled observe propose_only].include?(optimization_mode)
  errors << "self_optimization.mode must be disabled, observe, or propose_only"
end
if %w[observe propose_only].include?(optimization_mode) && !present?(self_optimization["event_store_ref"])
  errors << "self_optimization.event_store_ref is required when optimization is enabled"
end
if optimization_mode == "propose_only"
  errors << "self_optimization.replay_cases_ref is required in propose_only mode" unless present?(self_optimization["replay_cases_ref"])
  errors << "self_optimization.team_overlay_ref is required in propose_only mode" unless present?(self_optimization["team_overlay_ref"])
end
errors << "self_optimization.auto_modify_core must remain false" unless self_optimization["auto_modify_core"] == false
errors << "self_optimization.promotion_requires_human_alignment must remain true" unless self_optimization["promotion_requires_human_alignment"] == true

domain_effective = case mode
                   when "d3a"
                     overrides = value_at(config, "domain", "d3a", "dt_domains") || []
                     {
                       "id" => "d3a",
                       "source" => "builtin",
                       "lane_applicability" => "not_applicable",
                       "execution_profile" => "d3a_fixed_workflow",
                       "coding_layers_source" => "registries/d3a-layers.yaml",
                       "test_domains_source" => overrides.empty? ? "registries/dt-domains.yaml" : "team-config.yaml",
                       "test_domains" => overrides
                     }
                   when "general"
                     {
                       "id" => "general",
                       "source" => "builtin",
                       "lane_applicability" => "applicable",
                       "execution_profile" => "lane_driven",
                       "components" => value_at(config, "general", "components") || [],
                       "test_domains" => value_at(config, "general", "test_domains") || []
                     }
                   when "custom"
                     {
                       "id" => custom["id"],
                       "source" => "team-config-inline",
                       "lane_policy" => custom["lane_policy"],
                       "trigger_rules" => custom["trigger_rules"],
                       "coding_layers" => custom["coding_layers"],
                       "test_domains" => custom["test_domains"],
                       "required_contracts" => custom["required_contracts"],
                       "workflow_skill_ref" => custom["workflow_skill_ref"],
                       "planner_skill_ref" => custom["planner_skill_ref"],
                       "completion_skill_ref" => custom["completion_skill_ref"]
                     }
                   else
                     {}
                   end

capability_registry_path = harness_root.join(".claude/skills/idc-workflow/references/registries/team-capabilities.yaml")
capability_rows = []
if capability_registry_path.file?
  begin
    registry = YAML.safe_load(capability_registry_path.read, permitted_classes: [], aliases: false) || {}
    capability_rows = registry["team_capabilities"] || []
  rescue Psych::Exception => e
    errors << "team capability registry is invalid: #{e.message}"
  end
else
  errors << "team capability registry is missing: #{capability_registry_path}"
end

available_capabilities = []
capability_rows.each do |row|
  skill_ref = dotted_value(config, row["binding_path"])
  available_capabilities << row.merge("skill_ref" => skill_ref, "source" => "fixed-binding") if present?(skill_ref)
end
extensions.each do |entry|
  next unless entry.is_a?(Hash) && present?(entry["skill_ref"])
  available_capabilities << entry.merge(
    "binding_path" => "adapter_extensions",
    "eligible_lanes" => entry["eligible_lanes"] || %w[fast lite complex],
    "execution_profiles" => entry["execution_profiles"] || [],
    "trigger_signals" => entry["trigger_signals"] || [],
    "source" => "adapter-extension"
  )
end

registration_conflicts = []
registration_overrides = []
available_ids = available_capabilities.map { |capability| capability["id"] }
duplicate_ids = available_ids.group_by(&:itself).select { |_id, values| values.length > 1 }.keys
errors << "available capability IDs are duplicated: #{duplicate_ids.join(', ')}" if duplicate_ids.any?

available_capabilities.each do |capability|
  Array(capability["composes_with"]) .each do |target|
    errors << "#{capability['id']}.composes_with references unavailable capability: #{target}" unless available_ids.include?(target)
  end
  Array(capability["supersedes"]).each do |target|
    errors << "#{capability['id']}.supersedes references unavailable capability: #{target}" unless available_ids.include?(target)
    errors << "#{capability['id']} cannot supersede itself" if target == capability["id"]
  end
end

available_capabilities.combination(2).each do |left, right|
  shared_keys = Array(left["capability_keys"]) & Array(right["capability_keys"])
  shared_stages = Array(left["allowed_stages"]) & Array(right["allowed_stages"])
  shared_lanes = Array(left["eligible_lanes"]) & Array(right["eligible_lanes"])
  shared_profiles = Array(left["execution_profiles"]) & Array(right["execution_profiles"])
  both_unscoped = Array(left["eligible_lanes"]).empty? && Array(right["eligible_lanes"]).empty? &&
                  Array(left["execution_profiles"]).empty? && Array(right["execution_profiles"]).empty?
  next if shared_keys.empty? || shared_stages.empty? || (shared_lanes.empty? && shared_profiles.empty? && !both_unscoped)

  left_signals = Array(left["trigger_signals"])
  right_signals = Array(right["trigger_signals"])
  signals_overlap = left_signals.empty? || right_signals.empty? || (left_signals & right_signals).any?
  next unless signals_overlap

  composed = Array(left["composes_with"]).include?(right["id"]) || Array(right["composes_with"]).include?(left["id"])
  superseded = Array(left["supersedes"]).include?(right["id"]) || Array(right["supersedes"]).include?(left["id"])
  detail = {
    "left" => left["id"],
    "right" => right["id"],
    "capability_keys" => shared_keys,
    "stages" => shared_stages,
    "lanes" => shared_lanes,
    "execution_profiles" => shared_profiles
  }
  if composed || superseded
    detail["resolution"] = composed ? "compose" : "supersede"
    registration_overrides << detail
  else
    registration_conflicts << detail
    errors << "ambiguous capability registration: #{left['id']} conflicts with #{right['id']} on #{shared_keys.join(', ')} at #{shared_stages.join(', ')}"
  end
end

capability_by_id = available_capabilities.each_with_object({}) { |capability, index| index[capability["id"]] = capability }
%w[fast lite complex].each do |lane_id|
  profile = lane_profiles[lane_id]
  next unless profile.is_a?(Hash)

  skill_policy = profile["skills"].is_a?(Hash) ? profile["skills"] : {}
  configured_ids = %w[allow deny required].flat_map { |key| Array(skill_policy[key]) }
  steps = value_at(profile, "orchestration", "steps")
  configured_ids.concat(Array(steps).flat_map { |step| step.is_a?(Hash) ? Array(step["skill_ids"]) : [] })
  configured_ids.uniq.each do |skill_id|
    capability = capability_by_id[skill_id]
    if capability.nil?
      errors << "lane.profiles.#{lane_id} references unavailable skill ID: #{skill_id}"
      next
    end
    unless Array(capability["eligible_lanes"]).include?(lane_id)
      errors << "lane.profiles.#{lane_id} references lane-ineligible skill ID: #{skill_id}"
    end
  end

  Array(steps).each_with_index do |step, index|
    next unless step.is_a?(Hash) && present?(step["stage"])
    Array(step["skill_ids"]).each do |skill_id|
      capability = capability_by_id[skill_id]
      next unless capability
      unless Array(capability["allowed_stages"]).include?(step["stage"])
        errors << "lane.profiles.#{lane_id}.orchestration.steps[#{index}] uses #{skill_id} outside its allowed stage #{step['stage']}"
      end
    end
  end
end

effective = {
  "generated" => true,
  "source_ref" => config_path.to_s,
  "source_sha256" => Digest::SHA256.hexdigest(source_text),
  "config_version" => config["config_version"],
  "team" => config["team"].merge("repo_path" => team_root.to_s),
  "domain" => domain_effective,
  "bindings" => bindings.select { |_name, binding| binding.is_a?(Hash) && present?(binding["skill_ref"]) },
  "adapter_extensions" => extensions,
  "available_capabilities" => available_capabilities,
  "registration_audit" => {
    "status" => registration_conflicts.empty? ? "PASS" : "FAIL",
    "conflicts" => registration_conflicts,
    "declared_overrides" => registration_overrides
  },
  "knowledge" => config["knowledge"],
  "lane" => { "default" => lane_default, "profiles" => lane_profiles },
  "capability_selection" => capability_selection,
  "self_optimization" => self_optimization,
  "readiness" => {
    "status" => errors.empty? ? "READY" : "INVALID",
    "errors" => errors,
    "warnings" => warnings
  }
}

if errors.any?
  warn "INVALID team-config.yaml"
  errors.each { |error| warn "- #{error}" }
  exit 1
end

if options[:output]
  output_path = Pathname.new(options[:output]).expand_path
  FileUtils.mkdir_p(output_path.dirname)
  alias_free_effective = JSON.parse(JSON.generate(effective))
  temporary_path = output_path.dirname.join(".#{output_path.basename}.tmp-#{Process.pid}")
  temporary_path.write("# Generated by idc-team-config. Do not edit.\n" + YAML.dump(alias_free_effective))
  File.rename(temporary_path, output_path)
  puts "READY: wrote #{output_path}"
else
  puts "READY: team-config.yaml is valid"
end
