#!/usr/bin/env ruby
# frozen_string_literal: true

require "digest"
require "fileutils"
require "json"
require "optparse"
require "pathname"
require "yaml"
require_relative "../../idc-team-config/scripts/compat_ruby21"

options = {}
OptionParser.new do |parser|
  parser.banner = "Usage: authorize_execution.rb --request PATH [--output PATH]"
  parser.on("--request PATH") { |value| options[:request] = value }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!
abort "ERROR: --request is required" unless options[:request]

request_path = Pathname.new(options[:request]).expand_path
begin
  document = IDCRubyCompat.safe_yaml_load(request_path.read) || {}
rescue Errno::ENOENT, Psych::Exception => e
  abort "ERROR: #{e.message}"
end
request = document["execution_authorization_request"] || document

def present?(value)
  !value.nil? && value != "" && value != [] && value != {}
end

errors = []
errors << "human_alignment_status must be approved" unless request["human_alignment_status"] == "approved"
errors << "capability_selection_status must be READY" unless request["capability_selection_status"] == "READY"
errors << "main_agent_role must be planning_and_delegation_only" unless request["main_agent_role"] == "planning_and_delegation_only"

plan_confirmation = request["technical_plan_confirmation"]
plan_confirmation_errors = []
if plan_confirmation.is_a?(Hash)
  plan_confirmation_errors << "technical_plan_confirmation.required must be true (framework floor)" unless plan_confirmation["required"] == true
  valid_trigger_reasons = ["d3a_fixed_workflow", "lane=fast", "lane=lite", "lane=complex"]
  unless valid_trigger_reasons.include?(plan_confirmation["trigger_reason"].to_s)
    plan_confirmation_errors << "technical_plan_confirmation.trigger_reason must be d3a_fixed_workflow or lane=fast|lite|complex"
  end
  if plan_confirmation["status"] == "confirmed"
    unless present?(plan_confirmation["confirmation_ref"])
      plan_confirmation_errors << "technical_plan_confirmation.confirmation_ref is required when status is confirmed"
    end
    if present?(plan_confirmation["confirmation_ref"])
      plan_path = Pathname.new(plan_confirmation["confirmation_ref"].to_s).expand_path
      unless plan_path.file?
        plan_confirmation_errors << "technical_plan_confirmation.confirmation_ref file does not exist: #{plan_confirmation['confirmation_ref']}"
      end
    end
  else
    plan_confirmation_errors << "technical_plan_confirmation.status must be confirmed when required is true (framework floor)"
  end
else
  plan_confirmation_errors << "technical_plan_confirmation is required (framework floor: d3a and all lanes)"
end
errors.concat(plan_confirmation_errors)

%w[approved_alignment_ref execution_unit_ref context_packet_ref capability_selection_ref knowledge_load_plan_ref knowledge_plan_id domain_execution_skill_ref delegation_contract_ref].each do |key|
  errors << "#{key} is required" unless present?(request[key])
end
errors << "knowledge_load_plan_status must be READY" unless request["knowledge_load_plan_status"] == "READY"
errors << "allowed_paths must not be empty" unless present?(request["allowed_paths"])
errors << "expected_outputs must not be empty" unless present?(request["expected_outputs"])

executor = request["executor"] || {}
valid_executor_kinds = %w[subagent agent_team official_dynamic_workflow]
errors << "executor.kind must be subagent, agent_team, or official_dynamic_workflow" unless valid_executor_kinds.include?(executor["kind"])
errors << "executor.agent_id is required" unless present?(executor["agent_id"])
errors << "main_agent cannot be execution owner" if executor["agent_id"] == "main_agent" || executor["kind"] == "main_agent"

domain_skill = request["domain_execution_skill_ref"].to_s
case request["selected_domain"]
when "general"
  errors << "general execution must load idc-general-coding" unless domain_skill.include?("idc-general-coding")
when "d3a"
  errors << "d3a execution must load idc-d3a-coding" unless domain_skill.include?("idc-d3a-coding")
end

if present?(request["capability_selection_ref"])
  cap_sel_path = Pathname.new(request["capability_selection_ref"].to_s).expand_path
  begin
    cap_doc = IDCRubyCompat.safe_yaml_load(cap_sel_path.read) || {}
    cap_result = cap_doc["capability_selection_result"] || {}
    errors << "capability selection status must be READY (got #{cap_result['status'].inspect})" unless cap_result["status"] == "READY"
    errors << "capability selection execution_unit_ref does not match request" unless cap_result["execution_unit_ref"] == request["execution_unit_ref"]
    errors << "capability selection selected_skills must not be empty" unless Array(cap_result["selected"]).any?
  rescue Errno::ENOENT, Psych::Exception => e
    errors << "capability_selection_ref cannot be read: #{e.message}"
  end
end

harness_root = Pathname.new(__dir__).join("../../..").expand_path
team_config_path = harness_root.join("team-config.yaml")
# Allow the request to supply an explicit effective_config_ref (used in tests
# and multi-repo setups where the effective config lives outside harness_root).
effective_config_path = if present?(request["effective_config_ref"])
                           Pathname.new(request["effective_config_ref"].to_s).expand_path
                         else
                           harness_root.join(".idc/effective-team-config.yaml")
                         end
if team_config_path.file? && effective_config_path.file?
  begin
    effective_doc = IDCRubyCompat.safe_yaml_load(effective_config_path.read) || {}
    recorded_sha = effective_doc["source_sha256"].to_s
    actual_sha = Digest::SHA256.hexdigest(team_config_path.read)
    unless recorded_sha == actual_sha
      errors << "BLOCKED_STALE_EFFECTIVE_CONFIG: team-config.yaml has changed since last prepare_runtime.rb " \
                "(recorded=#{recorded_sha[0, 12]}… actual=#{actual_sha[0, 12]}…); " \
                "re-run prepare_runtime.rb and verify status: READY before authorizing"
    end
  rescue Errno::ENOENT, Psych::Exception => e
    errors << "effective config integrity check failed: #{e.message}"
  end
elsif team_config_path.file? && !effective_config_path.file?
  errors << "BLOCKED_STALE_EFFECTIVE_CONFIG: .idc/effective-team-config.yaml does not exist; run prepare_runtime.rb first"
end

if present?(request["knowledge_load_plan_ref"])
  knowledge_plan_path = Pathname.new(request["knowledge_load_plan_ref"].to_s).expand_path
  begin
    knowledge_document = IDCRubyCompat.safe_yaml_load(knowledge_plan_path.read) || {}
    knowledge_plan = knowledge_document["knowledge_load_plan"] || {}
    errors << "knowledge load plan must be READY" unless knowledge_plan["status"] == "READY"
    knowledge_body = knowledge_plan.reject { |key, _value| key == "knowledge_plan_id" }
    computed_knowledge_plan_id = Digest::SHA256.hexdigest(JSON.generate(knowledge_body))
    errors << "knowledge plan integrity check failed" unless knowledge_plan["knowledge_plan_id"] == computed_knowledge_plan_id
    errors << "knowledge plan ID does not match" unless knowledge_plan["knowledge_plan_id"] == request["knowledge_plan_id"]
    errors << "knowledge plan execution unit does not match" unless knowledge_plan["execution_unit_ref"] == request["execution_unit_ref"]
    errors << "knowledge plan domain does not match" unless knowledge_plan["selected_domain"] == request["selected_domain"]
  rescue Errno::ENOENT, Psych::Exception => e
    errors << "knowledge load plan cannot be read: #{e.message}"
  end
end

canonical = JSON.generate(request.sort.to_h)
authorization_id = errors.empty? ? Digest::SHA256.hexdigest(canonical) : nil
status = if !plan_confirmation_errors.empty?
           "BLOCKED_PLAN_CONFIRMATION_REQUIRED"
         elsif errors.empty?
           "AUTHORIZED"
         else
           "BLOCKED_DELEGATION_REQUIRED"
         end
result = {
  "execution_authorization_result" => {
    "status" => status,
    "authorization_id" => authorization_id,
    "execution_unit_ref" => errors.empty? ? request["execution_unit_ref"] : nil,
    "selected_domain" => errors.empty? ? request["selected_domain"] : nil,
    "selected_lane" => errors.empty? ? request["selected_lane"] : nil,
    "executor_kind" => errors.empty? ? executor["kind"] : nil,
    "domain_execution_skill_ref" => errors.empty? ? request["domain_execution_skill_ref"] : nil,
    "knowledge_load_plan_ref" => errors.empty? ? request["knowledge_load_plan_ref"] : nil,
    "knowledge_plan_id" => errors.empty? ? request["knowledge_plan_id"] : nil,
    "technical_plan_confirmation" => errors.empty? ? plan_confirmation : nil,
    "selected_atomic_skill_refs" => errors.empty? ? Array(request["selected_atomic_skill_refs"]) : [],
    "allowed_paths" => errors.empty? ? Array(request["allowed_paths"]) : [],
    "expected_outputs" => errors.empty? ? Array(request["expected_outputs"]) : [],
    "errors" => errors
  }
}

output = YAML.dump(result)
if options[:output]
  output_path = Pathname.new(options[:output]).expand_path
  FileUtils.mkdir_p(output_path.dirname)
  output_path.write(output)
else
  puts output
end
exit(errors.empty? ? 0 : 3)
