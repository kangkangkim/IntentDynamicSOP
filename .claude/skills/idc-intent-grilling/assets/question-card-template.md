# Question Card Template

```text
### Q<index>. <question>

- A. <option label> <recommended marker if applicable>
  - Impact: <what this changes>
- B. <option label>
  - Impact: <what this changes>
- C. <option label>
  - Impact: <what this changes>
- Other / 补充说明: <only when needed>

Blocks:
- <api_contract | verification_contract | scope_boundary | completion_gate>

Why needed:
<one sentence explaining why this blocks alignment>
```

## Rendering Rules

- Keep the question under 240 characters.
- Use 2-4 options.
- Mark at most one recommended option.
- Do not combine unrelated decisions in one card.
- Do not show raw YAML to the user.
