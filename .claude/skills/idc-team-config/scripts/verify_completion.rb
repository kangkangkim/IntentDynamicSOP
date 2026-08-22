#!/usr/bin/env ruby
# frozen_string_literal: true

require "optparse"
require "pathname"
require "yaml"
require_relative "compat_ruby21"

options = {}
OptionParser.new do |parser|
  parser.banner = "Usage: verify_completion.rb --request PATH [--output PATH]"
  parser.on("--request PATH") { |value| options[:request] = value }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!
abort "ERROR: --request is required" unless options[:request]

def load_yaml(path)
  IDCRubyCompat.safe_yaml_load(Pathname.new(path).expand_path.read) || {}
rescue Errno::ENOENT, Psych::Exception => e
  abort "ERROR: #{e.message}"
end

def present?(value)
  !value.nil? && value != "" && value != [] && value != {}
end

document = load_yaml(options[:request])
request = document["completion_verification_request"] || document
errors = []

domain = request["selected_domain"]
lane = request["selected_lane"]
execution_unit_ref = request["execution_unit_ref"]
errors << "selected_domain must be general, d3a, or custom" unless %w[general d3a custom].include?(domain)
errors << "execution_unit_ref is required" unless present?(execution_unit_ref)
if %w[general custom].include?(domain) && !lane.nil?
  errors << "selected_lane must be fast, lite, or complex" unless %w[fast lite complex].include?(lane)
elsif domain == "general"
  errors << "General selected_lane must not be null"
elsif domain == "d3a" && !lane.nil?
  errors << "D3A selected_lane must be null"
end

authorization_document = present?(request["authorization_result_ref"]) ? load_yaml(request["authorization_result_ref"]) : {}
authorization = authorization_document["execution_authorization_result"] || {}
errors << "authorization result must be AUTHORIZED" unless authorization["status"] == "AUTHORIZED"

knowledge_document = present?(request["knowledge_consumption_result_ref"]) ? load_yaml(request["knowledge_consumption_result_ref"]) : {}
knowledge = knowledge_document["knowledge_consumption_result"] || {}
errors << "knowledge consumption result must be VERIFIED" unless knowledge["status"] == "VERIFIED"

receipt = request["execution_receipt"] || {}
%w[authorization_id dispatch_tool_call_ref executor_session_ref executor_kind loaded_domain_execution_skill_ref knowledge_plan_id knowledge_consumption_result_ref].each do |key|
  errors << "execution_receipt.#{key} is required" unless present?(receipt[key])
end
errors << "execution receipt authorization_id does not match" unless receipt["authorization_id"] == authorization["authorization_id"]
errors << "authorization execution_unit_ref does not match" unless authorization["execution_unit_ref"] == execution_unit_ref
errors << "authorization selected_domain does not match" unless authorization["selected_domain"] == domain
errors << "authorization selected_lane does not match" unless authorization["selected_lane"] == lane
errors << "execution receipt executor_kind does not match authorization" unless receipt["executor_kind"] == authorization["executor_kind"]
errors << "execution receipt Domain Skill does not match authorization" unless receipt["loaded_domain_execution_skill_ref"] == authorization["domain_execution_skill_ref"]
errors << "execution receipt atomic Skills do not match authorization" unless Array(receipt["executed_atomic_skill_refs"]) == Array(authorization["selected_atomic_skill_refs"])
errors << "execution receipt knowledge_plan_id does not match authorization" unless receipt["knowledge_plan_id"] == authorization["knowledge_plan_id"]
errors << "knowledge result knowledge_plan_id does not match execution receipt" unless knowledge["knowledge_plan_id"] == receipt["knowledge_plan_id"]
errors << "knowledge result execution_unit_ref does not match" unless knowledge["execution_unit_ref"] == execution_unit_ref
receipt_knowledge_ref = Pathname.new(receipt["knowledge_consumption_result_ref"].to_s).expand_path.to_s
request_knowledge_ref = Pathname.new(request["knowledge_consumption_result_ref"].to_s).expand_path.to_s
errors << "execution receipt knowledge consumption result ref does not match" unless receipt_knowledge_ref == request_knowledge_ref
errors << "execution_receipt.changed_paths must not be empty" unless present?(receipt["changed_paths"])
errors << "execution_receipt.evidence_refs must not be empty" unless present?(receipt["evidence_refs"])
allowed_paths = Array(authorization["allowed_paths"]).map { |path| path.to_s.sub(%r{/+$}, "") }
Array(receipt["changed_paths"]).each do |changed_path|
  covered = allowed_paths.any? { |allowed| changed_path.to_s == allowed || changed_path.to_s.start_with?("#{allowed}/") }
  errors << "changed path is outside authorization: #{changed_path}" unless covered
end

loaded_domain_skill = receipt["loaded_domain_execution_skill_ref"].to_s
if domain == "general"
  errors << "general completion must load idc-general-coding" unless loaded_domain_skill.include?("idc-general-coding")
elsif domain == "d3a"
  errors << "d3a completion must load idc-d3a-coding" unless loaded_domain_skill.include?("idc-d3a-coding")
end

evidence = request["evidence"] || {}
required_evidence = if domain == "d3a"
                      %w[d3a_specification_ref api_contract_ref completion_summary_ref]
                    elsif domain == "custom" && lane.nil?
                      %w[custom_completion_evidence_refs completion_summary_ref]
                    elsif lane == "fast"
                      %w[task_summary_ref acceptance_criteria_ref changed_files_review_ref verification_evidence_refs completion_summary_ref]
                    elsif lane == "lite"
                      %w[task_contract_ref acceptance_criteria_ref focused_plan_ref relevant_context_refs verification_evidence_refs completion_summary_ref]
                    else
                      %w[task_contract_ref detailed_plan_ref evidence_plan_ref verification_evidence_refs audit_or_review_ref completion_summary_ref]
                    end
required_evidence.each do |key|
  errors << "evidence.#{key} is required for #{domain == 'd3a' ? 'd3a' : lane} completion" unless present?(evidence[key])
end

if %w[general custom].include?(domain) && request["test_based_verification"] == true && !lane.nil? && lane != "fast"
  coverage_present = present?(evidence["coverage_evidence_ref"])
  exemption = evidence["coverage_exemption"] || {}
  exemption_present = present?(exemption["reason"])
  errors << "coverage evidence or a reasoned exemption is required" unless coverage_present || exemption_present
end

if domain == "d3a"
  d3a = request["d3a"] || {}
  required_domains = Array(d3a["required_dt_domains"])
  errors << "d3a.required_dt_domains must not be empty" if required_domains.empty?
  errors << "d3a.required_dt_domains must contain unique IDs" unless required_domains.uniq.length == required_domains.length
  red = d3a["red_evidence_by_domain"] || {}
  green = d3a["green_evidence_by_domain"] || {}
  required_domains.each do |dt_domain|
    errors << "missing RED evidence for DT domain #{dt_domain}" unless present?(red[dt_domain])
    errors << "missing GREEN evidence for DT domain #{dt_domain}" unless present?(green[dt_domain])
  end
  errors << "d3a.tran_build_status must be PASS" unless d3a["tran_build_status"] == "PASS"
  errors << "d3a.tran_build_evidence_ref is required" unless present?(d3a["tran_build_evidence_ref"])
end

result = {
  "completion_verification_result" => {
    "status" => errors.empty? ? "DONE" : "BLOCKED_COMPLETION",
    "selected_domain" => domain,
    "selected_lane" => lane,
    "execution_unit_ref" => execution_unit_ref,
    "authorization_id" => errors.empty? ? receipt["authorization_id"] : nil,
    "knowledge_plan_id" => errors.empty? ? receipt["knowledge_plan_id"] : nil,
    "errors" => errors
  }
}

output = YAML.dump(result)
if options[:output]
  output_path = Pathname.new(options[:output]).expand_path
  output_path.dirname.mkpath
  output_path.write(output)
else
  puts output
end
exit(errors.empty? ? 0 : 4)
