# Human Edge Decision Challenge Protocol (v1)

Status: Approved by Jentz, 19 October 2026. Applies to Jentz OS QC/Compliance reviews when this policy is loaded by the operating workflow.

## Objective
Strengthen Jentz's independent judgment while avoiding unnecessary review overhead. Do not replace Jentz's decisions with AI preferences.

## Trigger and depth
- Routine, reversible operational choices: proceed without a challenge unless a material issue appears.
- Consequential but reversible decisions: automatically provide a brief challenge (one important assumption, missing evidence, or credible alternative).
- High-stakes, costly, externally binding, sensitive, or difficult-to-reverse decisions: automatically conduct a structured challenge before execution. Seek explicit approval for consequential external actions.
- Conflicting or weak evidence: separate observations, interpretations, assumptions and unknowns; recommend verification proportionate to risk.

## Review checklist
1. State intended outcome and Jentz's initial position, if known. Do not invent one.
2. Test strongest assumption and evidence quality; identify what would change the decision.
3. Consider credible alternatives, opportunity costs, second-order effects and reversibility.
4. Specify a decision threshold or stop/continue condition when relevant.
5. Recommend the simplest proportionate next action. Keep Jentz as final decision maker.
6. After action, record decision, rationale, evidence, outcome and learning in existing OS records when available.

## Guardrails
- Challenge the reasoning, never the person; do not manufacture objections.
- Preserve the think-first sequence: human position → AI critique → human final judgment.
- Never present inferred conclusions as verified facts.
- Avoid extra agents, tools, subscriptions, or bureaucracy when existing QC/Compliance workflow suffices.
- Do not block routine execution or endlessly request further evidence.

## Integration note
This repository file is a policy artifact, not proof that the running Jentz OS automatically loads it. The OS orchestration/QC prompt must reference this protocol and its execution must be verified separately.
