#!/usr/bin/env ruby
# frozen_string_literal: true

require "optparse"
require "pathname"
require "yaml"

PHASES = %w[bootstrap decision planning execution completion resume].freeze
DOMAINS = %w[general d3a custom].freeze
LANES = %w[fast lite complex].freeze

ROOT = Pathname.new(__dir__).join("../../../..").expand_path

COMMON_REFS = {
  "bootstrap" => %w[
    .claude/skills/idc-workflow/references/workflows/input-adapter.md
    .claude/skills/idc-workflow/references/workflows/scenario-router.md
    .claude/skills/idc-workflow/references/workflows/domain-module-router.md
  ],
  "decision" => %w[
    .claude/skills/idc-workflow/references/constraints/decision/core-decision-constraints.yaml
    .claude/skills/idc-workflow/references/constraints/decision/contract-selection.yaml
    .claude/skills/idc-workflow/references/workflows/contract-gate.md
    .claude/skills/idc-workflow/references/workflows/requirement-assessor.md
    .claude/skills/idc-workflow/references/workflows/human-alignment.md
    .claude/skills/idc-workflow/references/schemas/alignment-pack.schema.yaml
    .claude/skills/idc-workflow/references/human-views/alignment-view.md
  ],
  "planning" => %w[
    .claude/skills/idc-workflow/references/constraints/planning/core-planning-constraints.yaml
    .claude/skills/idc-workflow/references/workflows/execution-unit-policy.md
    .claude/skills/idc-workflow/references/workflows/knowledge-gate.md
  ],
  "execution" => %w[
    .claude/skills/idc-workflow/references/constraints/execution/core-execution-constraints.yaml
    .claude/skills/idc-workflow/references/constraints/execution/context-loading.yaml
    .claude/skills/idc-workflow/references/workflows/automated-closure-loop.md
    .claude/skills/idc-workflow/references/workflows/progressive-constraint-loading.md
    .claude/skills/idc-workflow/references/workflows/capability-selector.md
    .claude/skills/idc-workflow/references/workflows/delegation-router.md
    .claude/skills/idc-workflow/references/workflows/execution-authorization-gate.md
    .claude/skills/idc-workflow/references/schemas/delegation-contract.schema.yaml
    .claude/skills/idc-workflow/references/schemas/execution-authorization.schema.yaml
    .claude/skills/idc-skill-adapter-router/SKILL.md
  ],
  "completion" => %w[
    .claude/skills/idc-workflow/references/workflows/lane-completion.md
    .claude/skills/idc-workflow/references/schemas/verification-contract.schema.yaml
    .claude/skills/idc-workflow/references/schemas/escalation-policy.schema.yaml
    .claude/skills/idc-workflow/references/human-views/completion-view.md
    .claude/skills/idc-workflow/references/human-views/escalation-view.md
  ],
  "resume" => %w[
    .claude/skills/idc-workflow/references/workflows/resume-policy.md
    .claude/skills/idc-workflow/references/schemas/runtime-state.schema.yaml
    .claude/skills/idc-workflow/references/schemas/delegation-contract.schema.yaml
  ]
}.freeze

DOMAIN_REFS = {
  "general" => {
    "decision" => %w[
      .claude/skills/idc-workflow/references/domains/general/module.yaml
      .claude/skills/idc-workflow/references/workflows/lane-resolver.md
    ],
    "planning" => %w[
      .claude/skills/idc-workflow/references/workflows/general-coding.md
      .claude/skills/idc-workflow/references/schemas/general-plan.schema.yaml
    ],
    "execution" => %w[.claude/skills/idc-general-coding/SKILL.md]
  },
  "d3a" => {
    "decision" => %w[.claude/skills/idc-workflow/references/domains/d3a/module.yaml],
    "planning" => %w[
      .claude/skills/idc-workflow/references/constraints/planning/d3a-planning-constraints.yaml
      .claude/skills/idc-workflow/references/workflows/d3a-workflow.md
      .claude/skills/idc-workflow/references/schemas/d3a-plan.schema.yaml
    ],
    "execution" => %w[
      .claude/skills/idc-workflow/references/constraints/execution/d3a-execution-constraints.yaml
      .claude/skills/idc-d3a-coding/SKILL.md
    ]
  },
  "custom" => {}
}.freeze

SIGNAL_REFS = {
  "raw_idea" => %w[
    .claude/skills/idc-brainstorming/SKILL.md
    .claude/skills/idc-intent-discovery/SKILL.md
    .claude/skills/idc-workflow/references/workflows/discovery-provider.md
    .claude/skills/idc-workflow/references/schemas/discovery-provider.schema.yaml
    .claude/skills/idc-workflow/references/human-views/brainstorming-view.md
  ],
  "clarification_required" => %w[
    .claude/skills/idc-intent-grilling/SKILL.md
    .claude/skills/idc-intent-grilling/references/grill-me-method.md
    .claude/skills/idc-workflow/references/workflows/clarification-provider.md
    .claude/skills/idc-workflow/references/schemas/clarification-provider.schema.yaml
    .claude/skills/idc-workflow/references/human-views/clarification-view.md
  ],
  "docs_clarification_required" => %w[
    .claude/skills/idc-intent-grilling-with-docs/SKILL.md
    .claude/skills/idc-intent-grilling-with-docs/references/grill-with-docs-method.md
  ],
  "user_question_required" => %w[.claude/skills/idc-workflow/references/workflows/ask-user-tool-policy.md],
  "tr3_input" => %w[
    .claude/skills/idc-workflow/references/schemas/normalized-request.schema.yaml
    .claude/skills/idc-workflow/references/docs/deep-dive/tr3-input.md
  ],
  "tdd_required" => %w[.claude/skills/idc-workflow/references/workflows/tdd-state-machine.md],
  "repo_context_required" => %w[
    .claude/skills/idc-workflow/CONTEXT_ENGINEERING.md
    .claude/skills/idc-workflow/references/workflows/provider-selection-matrix.md
    .claude/skills/idc-workflow/references/workflows/repo-context-providers.md
    .claude/skills/idc-workflow/references/schemas/repo-context-provider.schema.yaml
  ],
  "vertical_slice_readiness_required" => %w[
    .claude/skills/idc-workflow/references/workflows/vertical-slice-readiness-gate.md
    .claude/skills/idc-workflow/references/schemas/vertical-slice-readiness.schema.yaml
    docs/confidential-migration-checklist.md
  ]
}.freeze

# Framework-default alignment baseline: the five intent skills the resolver
# materializes (resolve_team_config.rb `alignment_default_bindings`) when
# team-config.yaml has no alignment section. Documented here so the source
# text carries the literal intent-alignment ref, and used as a fallback when a
# decision phase derives no skill refs from the effective pipeline.
FRAMEWORK_DEFAULT_ALIGNMENT_REFS = %w[
  .claude/skills/idc-intent-discovery/SKILL.md
  .claude/skills/idc-brainstorming/SKILL.md
  .claude/skills/idc-intent-grilling/SKILL.md
  .claude/skills/idc-intent-grilling-with-docs/SKILL.md
  .claude/skills/idc-intent-alignment/SKILL.md
].freeze

options = { signals: [] }
OptionParser.new do |parser|
  parser.banner = "Usage: plan_context.rb --effective PATH --phase PHASE [--domain DOMAIN] [--lane LANE] [--selection PATH] [--knowledge-plan PATH] [--signal SIGNAL]"
  parser.on("--effective PATH") { |value| options[:effective] = value }
  parser.on("--phase PHASE") { |value| options[:phase] = value }
  parser.on("--domain DOMAIN") { |value| options[:domain] = value }
  parser.on("--lane LANE") { |value| options[:lane] = value }
  parser.on("--selection PATH") { |value| options[:selection] = value }
  parser.on("--knowledge-plan PATH") { |value| options[:knowledge_plan] = value }
  parser.on("--signal SIGNAL") { |value| options[:signals] << value }
end.parse!

def fail_plan(message, exit_code = 2)
  puts YAML.dump("context_load_plan" => { "status" => "INVALID", "reason" => message })
  exit exit_code
end

def load_yaml(path)
  YAML.safe_load(Pathname.new(path).expand_path.read, permitted_classes: [], aliases: false) || {}
rescue Errno::ENOENT, Psych::Exception => e
  fail_plan(e.message)
end

def repo_relative_ref(ref)
  path = Pathname.new(ref.to_s)
  return ref.to_s unless path.absolute?
  relative = path.relative_path_from(ROOT).to_s
  relative.start_with?("..") ? path.to_s : relative
end

fail_plan("--effective and --phase are required") unless options[:effective] && options[:phase]
fail_plan("unknown phase: #{options[:phase]}") unless PHASES.include?(options[:phase])
fail_plan("unknown domain: #{options[:domain]}") if options[:domain] && !DOMAINS.include?(options[:domain])
fail_plan("unknown lane: #{options[:lane]}") if options[:lane] && !LANES.include?(options[:lane])
fail_plan("--domain is required after bootstrap") if options[:phase] != "bootstrap" && !options[:domain]
fail_plan("--selection is required for execution") if options[:phase] == "execution" && !options[:selection]
fail_plan("--knowledge-plan is required for execution") if options[:phase] == "execution" && !options[:knowledge_plan]

effective = load_yaml(options[:effective])
fail_plan("effective config is not generated runtime state") unless effective["generated"] == true

# Gate 2: an explicitly requested --domain must match the effective config's
# domain, so a team that switched/unplugged a domain cannot still run sessions
# of the other domain. Bootstrap passes no --domain and stays exempt.
if options[:domain]
  effective_domain_id = effective.dig("domain", "id")
  effective_domain_source = effective.dig("domain", "source")
  domain_consistent =
    case options[:domain]
    when "general", "d3a"
      effective_domain_id == options[:domain]
    when "custom"
      effective_domain_source == "team-config-inline"
    else
      false
    end
  unless domain_consistent
    fail_plan(
      "--domain #{options[:domain]} does not match effective domain #{effective_domain_id || 'unknown'}; " \
      "switch team-config domain.mode or use the effective domain"
    )
  end
end

lane_applicable = options[:domain] == "general"
custom_lane_mode = nil
if options[:domain] == "custom"
  custom_lane_mode = effective.dig("domain", "lane_policy", "mode")
  lane_applicable = custom_lane_mode != "not_applicable"
  if custom_lane_mode == "fixed"
    fixed_lane = effective.dig("domain", "lane_policy", "selected_lane")
    if options[:lane] && options[:lane] != fixed_lane
      fail_plan(
        "--lane #{options[:lane]} conflicts with domain.custom.lane_policy.mode fixed selected_lane #{fixed_lane}; " \
        "omit --lane or update the fixed policy in team-config.yaml"
      )
    end
    options[:lane] ||= fixed_lane
  end
end
if lane_applicable && %w[planning execution completion].include?(options[:phase]) && !options[:lane]
  lane_default = effective.dig("lane", "default").to_s
  if lane_default.empty?
    fail_plan("--lane is required for a lane-applicable domain and the effective config has no lane.default fallback")
  end
  options[:lane] = lane_default
end

refs = Array(COMMON_REFS[options[:phase]])
refs.concat(Array(DOMAIN_REFS.dig(options[:domain], options[:phase]))) if options[:domain]

if options[:phase] == "decision"
  alignment = effective["alignment"]
  unless alignment.is_a?(Hash) && !alignment.empty?
    fail_plan("effective config is missing the materialized alignment pipeline; regenerate it with resolve_team_config.rb")
  end
  alignment_bindings = alignment["bindings"] || {}
  # Collect skill_ids across ALL orchestration steps (do not filter by stage —
  # the framework-default chain and a configured pipeline both express every
  # intent skill through their steps, not just the alignment_check step).
  alignment_steps = Array(alignment.dig("orchestration", "steps"))
  alignment_skill_ids = alignment_steps.flat_map do |step|
    step.is_a?(Hash) ? Array(step["skill_ids"]) : []
  end
  alignment_skill_refs = alignment_skill_ids.map do |skill_id|
    skill_ref = alignment_bindings.dig(skill_id, "skill_ref").to_s
    skill_ref.empty? ? nil : repo_relative_ref(skill_ref)
  end.compact.uniq
  if alignment_skill_refs.empty?
    alignment_skill_refs = FRAMEWORK_DEFAULT_ALIGNMENT_REFS.map { |ref| repo_relative_ref(ref) }
  end
  fail_plan("decision phase derived no alignment skill refs from the effective alignment pipeline") if alignment_skill_refs.empty?
  refs.concat(alignment_skill_refs)
end

if options[:domain] == "custom"
  custom_ref_key = {
    "planning" => "planner_skill_ref",
    "execution" => "workflow_skill_ref",
    "completion" => "completion_skill_ref"
  }[options[:phase]]
  custom_ref = effective.dig("domain", custom_ref_key) if custom_ref_key
  fail_plan("custom domain is missing #{custom_ref_key}") if custom_ref_key && custom_ref.to_s.empty?
  refs << custom_ref if custom_ref
end

# Surface the effective domain's declared required contracts in the planning
# plan so downstream contract gating sees them; the gate workflow ref rides
# along so the plan is self-contained for contract enforcement.
required_contracts = Array(effective.dig("domain", "required_contracts")).map(&:to_s)
if options[:phase] == "planning" && required_contracts.any?
  refs << ".claude/skills/idc-workflow/references/workflows/contract-gate.md"
end

# Lane Resolver owns dynamic lane selection only (lane-resolver.md): a fixed
# lane policy pins selected_lane up front and not_applicable domains are
# handled by their execution profile, so neither injects the resolver ref.
refs << ".claude/skills/idc-workflow/references/workflows/lane-resolver.md" if custom_lane_mode == "dynamic" && options[:domain] == "custom" && options[:phase] == "decision"
if lane_applicable && options[:lane] && %w[decision planning execution completion].include?(options[:phase])
  refs << ".claude/skills/idc-workflow/references/lanes/#{options[:lane]}.yaml"
end

unknown_signals = options[:signals] - SIGNAL_REFS.keys
fail_plan("unknown signal(s): #{unknown_signals.join(', ')}") if unknown_signals.any?
options[:signals].each { |signal| refs.concat(SIGNAL_REFS.fetch(signal)) }

selected_capabilities = []
selection = nil
if options[:selection]
  selection = load_yaml(options[:selection]).fetch("capability_selection_result", {})
  fail_plan("capability selection is not READY") unless selection["status"] == "READY"
  selected_capabilities = Array(selection["selected"]).map do |item|
    {
      "capability_id" => item["capability_id"],
      "skill_ref" => item["skill_ref"],
      "execution_order" => item["execution_order"]
    }
  end
  refs.concat(selected_capabilities.map { |item| item["skill_ref"] })
end

knowledge_plan = nil
if options[:knowledge_plan]
  knowledge_plan = load_yaml(options[:knowledge_plan]).fetch("knowledge_load_plan", {})
  fail_plan("knowledge load plan is not READY") unless knowledge_plan["status"] == "READY"
  fail_plan("knowledge load plan source does not match effective config") unless knowledge_plan["source_sha256"] == effective["source_sha256"]
  fail_plan("knowledge load plan domain does not match context domain") unless knowledge_plan["selected_domain"] == options[:domain]
  if selection && knowledge_plan["execution_unit_ref"] != selection["execution_unit_ref"]
    fail_plan("knowledge load plan execution unit does not match capability selection")
  end
  provider_skill_ref = knowledge_plan.dig("repo_context", "provider_skill_ref")
  if knowledge_plan.dig("repo_context", "required") == true && knowledge_plan.dig("repo_context", "mode") == "bound_skill"
    fail_plan("bound repo context mode is missing provider_skill_ref") if provider_skill_ref.to_s.empty?
    refs << provider_skill_ref
  end
end

refs = refs.compact.map(&:to_s).reject(&:empty?).uniq
missing_refs = refs.reject do |ref|
  path = Pathname.new(ref)
  path = ROOT.join(path) unless path.absolute?
  path.file?
end
fail_plan("planned reference(s) do not exist: #{missing_refs.join(', ')}") if missing_refs.any?

context_plan = {
  "status" => "READY",
  "source_sha256" => effective["source_sha256"],
  "phase" => options[:phase],
  "domain" => options[:domain],
  "lane" => options[:lane],
  "signals" => options[:signals],
  "required_refs" => refs,
  "selected_capabilities" => selected_capabilities,
  "knowledge_load_plan_ref" => options[:knowledge_plan] && Pathname.new(options[:knowledge_plan]).expand_path.to_s,
  "knowledge_plan_id" => knowledge_plan && knowledge_plan["knowledge_plan_id"],
  "required_static_knowledge" => knowledge_plan ? Array(knowledge_plan["required_static_knowledge"]) : [],
  "knowledge_search_scopes" => knowledge_plan ? Array(knowledge_plan["search_scopes"]) : [],
  "repo_context_plan" => knowledge_plan ? knowledge_plan["repo_context"] : nil,
  "load_policy" => "read_required_refs_only"
}
context_plan["required_contracts"] = required_contracts if options[:phase] == "planning" && required_contracts.any?

puts YAML.dump("context_load_plan" => context_plan)
