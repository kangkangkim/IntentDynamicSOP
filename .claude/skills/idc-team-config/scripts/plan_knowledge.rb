#!/usr/bin/env ruby
# frozen_string_literal: true

require "digest"
require "json"
require "optparse"
require "pathname"
require "yaml"

options = {}
OptionParser.new do |parser|
  parser.banner = "Usage: plan_knowledge.rb --effective PATH --demand PATH [--output PATH]"
  parser.on("--effective PATH") { |value| options[:effective] = value }
  parser.on("--demand PATH") { |value| options[:demand] = value }
  parser.on("--output PATH") { |value| options[:output] = value }
end.parse!

abort "ERROR: --effective and --demand are required" unless options[:effective] && options[:demand]

def load_yaml(path)
  YAML.safe_load(Pathname.new(path).expand_path.read, permitted_classes: [], aliases: false) || {}
rescue Errno::ENOENT, Psych::Exception => e
  abort "ERROR: #{e.message}"
end

def present?(value)
  !value.nil? && value != "" && value != [] && value != {}
end

effective = load_yaml(options[:effective])
demand_document = load_yaml(options[:demand])
demand = demand_document["knowledge_demand"] || demand_document

errors = []
errors << "effective config is not generated runtime state" unless effective["generated"] == true
execution_unit_ref = demand["execution_unit_ref"]
domain = demand["selected_domain"]
errors << "execution_unit_ref is required" unless present?(execution_unit_ref)
errors << "selected_domain must be general, d3a, or custom" unless %w[general d3a custom].include?(domain)

selected_layer = demand["selected_layer"]
selected_components = Array(demand["selected_components"])
selected_test_domains = Array(demand["selected_test_domains"])
errors << "selected_components must contain unique IDs" unless selected_components.uniq.length == selected_components.length
errors << "selected_test_domains must contain unique IDs" unless selected_test_domains.uniq.length == selected_test_domains.length

if domain == "d3a"
  errors << "selected_layer is required for D3A knowledge" unless present?(selected_layer)
  errors << "D3A knowledge requires at least one selected_test_domain" if selected_test_domains.empty?
  errors << "D3A knowledge cannot select General components" if selected_components.any?
elsif domain == "general"
  errors << "General knowledge cannot select a Layer" if present?(selected_layer)
elsif domain == "custom"
  errors << "selected_layer is required for Custom Domain knowledge" unless present?(selected_layer)
  errors << "Custom Domain knowledge cannot select General components" if selected_components.any?
end

catalog = effective.dig("knowledge_catalog", domain) || {}
knowledge = effective["knowledge"] || {}
selected_entries = []
scope_entries = []

select_entry = lambda do |entries, id, kind|
  entry = Array(entries).find { |candidate| candidate.is_a?(Hash) && candidate["id"] == id }
  if entry.nil?
    errors << "#{kind} is not available in effective knowledge catalog: #{id}"
    next
  end
  ref = entry["knowledge_ref"]
  if present?(ref)
    selected_entries << {
      "kind" => kind,
      "id" => id,
      "ref" => ref,
      "source" => "knowledge_catalog"
    }
  else
    errors << "#{kind} has no knowledge_ref: #{id}"
  end
end

if present?(selected_layer)
  layer_override = (knowledge["layer_docs"] || {})[selected_layer]
  if present?(layer_override)
    selected_entries << {
      "kind" => "layer",
      "id" => selected_layer,
      "ref" => layer_override,
      "source" => "knowledge.layer_docs"
    }
  else
    select_entry.call(catalog["layers"], selected_layer, "layer")
  end
end
selected_components.each { |id| select_entry.call(catalog["components"], id, "component") }
selected_test_domains.each { |id| select_entry.call(catalog["test_domains"], id, "test_domain") }

{
  "architecture" => ["include_architecture", "architecture_doc_ref"],
  "verification_mapping" => ["include_verification_mapping", "verification_mapping_ref"]
}.each do |kind, (demand_key, knowledge_key)|
  next unless demand[demand_key] == true
  ref = knowledge[knowledge_key]
  if present?(ref)
    selected_entries << { "kind" => kind, "id" => kind, "ref" => ref, "source" => "knowledge.#{knowledge_key}" }
  else
    errors << "#{knowledge_key} is required by knowledge demand"
  end
end

if demand["include_feature_docs_scope"] == true
  feature_root = knowledge["feature_docs_root_ref"]
  if present?(feature_root)
    scope_entries << {
      "kind" => "feature_docs_scope",
      "id" => "feature_docs_root",
      "ref" => feature_root,
      "source" => "knowledge.feature_docs_root_ref"
    }
  else
    errors << "feature_docs_root_ref is required by knowledge demand"
  end
end

repo_context = knowledge["repo_context"] || {}
repo_context_required = demand["repo_context_required"] == true
provider_mode = if present?(repo_context["provider_skill_ref"])
                  "bound_skill"
                elsif repo_context["fallback"] == "bounded_grep"
                  "bounded_grep"
                else
                  "none"
                end
if repo_context_required && provider_mode == "none"
  errors << "repo context is required but no provider_skill_ref or bounded_grep fallback is available"
end

body = {
  "status" => errors.empty? ? "READY" : "NEEDS_KNOWLEDGE_MAPPING",
  "source_sha256" => effective["source_sha256"],
  "execution_unit_ref" => execution_unit_ref,
  "selected_domain" => domain,
  "selected_layer" => selected_layer,
  "selected_components" => selected_components,
  "selected_test_domains" => selected_test_domains,
  "required_static_knowledge" => selected_entries,
  "search_scopes" => scope_entries,
  "repo_context" => {
    "required" => repo_context_required,
    "mode" => provider_mode,
    "provider_skill_ref" => repo_context["provider_skill_ref"],
    "policy_ref" => repo_context["policy_ref"],
    "fallback" => repo_context["fallback"]
  },
  "consumption_policy" => {
    "all_required_static_refs_must_be_loaded" => true,
    "unplanned_static_refs_forbidden" => true,
    "search_scope_result_required" => scope_entries.any?,
    "provider_result_required" => repo_context_required
  },
  "errors" => errors
}
body["knowledge_plan_id"] = Digest::SHA256.hexdigest(JSON.generate(body)) if errors.empty?

output = YAML.dump("knowledge_load_plan" => body)
if options[:output]
  Pathname.new(options[:output]).expand_path.write(output)
else
  puts output
end
exit(errors.empty? ? 0 : 2)
