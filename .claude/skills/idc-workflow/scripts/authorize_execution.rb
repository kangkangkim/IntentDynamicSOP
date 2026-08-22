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
result = {
  "execution_authorization_result" => {
    "status" => errors.empty? ? "AUTHORIZED" : "BLOCKED_DELEGATION_REQUIRED",
    "authorization_id" => authorization_id,
    "execution_unit_ref" => errors.empty? ? request["execution_unit_ref"] : nil,
    "selected_domain" => errors.empty? ? request["selected_domain"] : nil,
    "selected_lane" => errors.empty? ? request["selected_lane"] : nil,
    "executor_kind" => errors.empty? ? executor["kind"] : nil,
    "domain_execution_skill_ref" => errors.empty? ? request["domain_execution_skill_ref"] : nil,
    "knowledge_load_plan_ref" => errors.empty? ? request["knowledge_load_plan_ref"] : nil,
    "knowledge_plan_id" => errors.empty? ? request["knowledge_plan_id"] : nil,
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
