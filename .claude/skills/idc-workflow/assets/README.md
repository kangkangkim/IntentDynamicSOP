# IDC Assets

Assets are static resources used by skills.

They are not instructions and they are not workflow references.

## Official Skill Directory Shape

```text
skill-name/
  SKILL.md
  scripts/
  references/
  assets/
```

Use this harness convention:

```text
.claude/skills/<name>/SKILL.md
  executable behavior, routing, gates, adapters, or handoffs

.claude/skills/<name>/references/
  additional documentation loaded on demand

.claude/skills/<name>/assets/
  static resources such as templates, images, or data files

.claude/skills/<name>/scripts/
  executable helper code
```

## What Belongs In Assets

Use `assets/` for static resources:

- reusable templates.
- sample data.
- images.
- static diagrams.
- fixtures intended as resources for a skill.

## What Belongs In References

Use `references/` for additional documentation:

- workflow explanations.
- schema documentation.
- registry documentation.
- human-view instructions.
- knowledge reference docs.
- adoption or migration reference notes that a skill may load on demand.

## Rules

- Do not put active routing logic in `assets/`.
- Do not put static resource files in `references/` when they are templates, images, or data.
- Do not create a skill for passive data.
- Enterprise-specific assets must use explicit placeholders outside team-config onboarding.
