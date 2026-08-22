#!/usr/bin/env ruby
# frozen_string_literal: true

require "optparse"
require "pathname"
require "digest"
require "json"
require "yaml"

options = {}
OptionParser.new do |parser|
  parser.banner = "Usage: verify_knowledge_consumption.rb --plan PATH --receipt PATH [--output PATH]"
  parser.on("--plan PATH") { |value| options[:plan] = value }
  parser.on("--receipt PATH") { |value| options[:receipt] = value }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!

abort "ERROR: --plan and --receipt are required" unless options[:plan] && options[:receipt]

def load_yaml(path)
  YAML.safe_load(Pathname.new(path).expand_path.read, permitted_classes: [], aliases: false) || {}
rescue Errno::ENOENT, Psych::Exception => e
  abort "ERROR: #{e.message}"
end

plan = load_yaml(options[:plan]).fetch("knowledge_load_plan", {})
receipt = load_yaml(options[:receipt]).fetch("knowledge_consumption_receipt", {})
errors = []

errors << "knowledge plan must be READY" unless plan["status"] == "READY"
plan_body = plan.reject { |key, _value| key == "knowledge_plan_id" }
computed_plan_id = Digest::SHA256.hexdigest(JSON.generate(plan_body))
errors << "knowledge plan integrity check failed" unless plan["knowledge_plan_id"] == computed_plan_id
errors << "knowledge_plan_id does not match" unless receipt["knowledge_plan_id"] == plan["knowledge_plan_id"]
errors << "execution_unit_ref does not match" unless receipt["execution_unit_ref"] == plan["execution_unit_ref"]

normalize_ref = lambda do |ref|
  value = ref.to_s
  value.match?(%r{^[a-z][a-z0-9+.-]*:}i) ? value : Pathname.new(value).expand_path.to_s
end
required_refs = Array(plan["required_static_knowledge"]).map { |entry| normalize_ref.call(entry["ref"]) }.uniq
required_refs.each do |ref|
  next if ref.match?(%r{^[a-z][a-z0-9+.-]*:}i)
  errors << "required local knowledge ref no longer exists: #{ref}" unless Pathname.new(ref).file?
end
loaded_refs = Array(receipt["loaded_static_refs"]).map { |ref| normalize_ref.call(ref) }
missing_refs = required_refs - loaded_refs
unplanned_refs = loaded_refs - required_refs
errors << "required knowledge refs were not loaded: #{missing_refs.join(', ')}" if missing_refs.any?
errors << "unplanned knowledge refs were loaded: #{unplanned_refs.join(', ')}" if unplanned_refs.any?

if Array(plan["search_scopes"]).any? && Array(receipt["search_scope_result_refs"]).empty?
  errors << "search_scope_result_refs are required"
end
if plan.dig("repo_context", "required") == true && Array(receipt["provider_result_refs"]).empty?
  errors << "provider_result_refs are required"
end
errors << "loaded knowledge must be summarized with evidence refs" if required_refs.any? && Array(receipt["knowledge_summary_refs"]).empty?

result = {
  "knowledge_consumption_result" => {
    "status" => errors.empty? ? "VERIFIED" : "BLOCKED_KNOWLEDGE_CONSUMPTION",
    "knowledge_plan_id" => plan["knowledge_plan_id"],
    "execution_unit_ref" => plan["execution_unit_ref"],
    "loaded_static_refs" => loaded_refs,
    "provider_result_refs" => Array(receipt["provider_result_refs"]),
    "search_scope_result_refs" => Array(receipt["search_scope_result_refs"]),
    "knowledge_summary_refs" => Array(receipt["knowledge_summary_refs"]),
    "errors" => errors
  }
}

output = YAML.dump(result)
if options[:output]
  Pathname.new(options[:output]).expand_path.write(output)
else
  puts output
end
exit(errors.empty? ? 0 : 3)
