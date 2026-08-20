#!/usr/bin/env ruby
# frozen_string_literal: true

require "digest"
require "fileutils"
require "json"
require "optparse"
require "pathname"
require "yaml"

options = {}
OptionParser.new do |parser|
  parser.banner = "Usage: authorize_execution.rb --request PATH [--output PATH]"
  parser.on("--request PATH") { |value| options[:request] = value }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!
abort "ERROR: --request is required" unless options[:request]

request_path = Pathname.new(options[:request]).expand_path
begin
  document = YAML.safe_load(request_path.read, permitted_classes: [], aliases: false) || {}
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

%w[approved_alignment_ref execution_unit_ref context_packet_ref capability_selection_ref domain_execution_skill_ref delegation_contract_ref].each do |key|
  errors << "#{key} is required" unless present?(request[key])
end
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

canonical = JSON.generate(request.sort.to_h)
authorization_id = errors.empty? ? Digest::SHA256.hexdigest(canonical) : nil
result = {
  "execution_authorization_result" => {
    "status" => errors.empty? ? "AUTHORIZED" : "BLOCKED_DELEGATION_REQUIRED",
    "authorization_id" => authorization_id,
    "executor_kind" => errors.empty? ? executor["kind"] : nil,
    "domain_execution_skill_ref" => errors.empty? ? request["domain_execution_skill_ref"] : nil,
    "selected_atomic_skill_refs" => errors.empty? ? Array(request["selected_atomic_skill_refs"]) : [],
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
