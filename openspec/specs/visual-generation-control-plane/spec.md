# Visual Generation Control Plane Specification

## Purpose
This spec captures the current v0.9 visual generation control plane on `main`. It covers workflow templates, validated slots, visual model inventory, strict-worldline character visual profiles, provider-neutral visual generation plans, ComfyUI execution boundaries, cross-provider mapping, and reviewable AI-assisted personalization.

## Requirements
### Requirement: Workflow Template Registry
The system SHALL support versioned workflow templates for image generation, editing, inpainting, reference-image generation, and composition. Workflow templates MAY represent ComfyUI workflow JSON, Z-Image request templates, GPT Image request templates, OpenAI-compatible image request templates, or generic image API request templates. Templates SHALL expose validated parameter slots instead of arbitrary raw execution payloads.

#### Scenario: Register ComfyUI workflow template
- **Given** an admin registers a ComfyUI workflow template
- **When** the template is saved
- **Then** the system SHALL record provider kind, adapter kind, intent, workflow key, version, required capabilities, parameter schema, allowed asset roles, safety constraints, and validation status
- **And** local workflow file paths SHALL NOT be exposed to reader/player/member APIs.

#### Scenario: Fill workflow template slots
- **Given** a workflow template exposes checkpoint, LoRA, prompt, reference image, seed, size, sampler, and output slots
- **When** a generation request uses the template
- **Then** only whitelisted slots SHALL be filled
- **And** unrecognized node changes or raw workflow payloads SHALL be rejected.

### Requirement: Visual Model Asset Inventory
The system SHALL represent checkpoint, LoRA, VAE, embedding, ControlNet, IP-Adapter, workflow template, and prompt preset assets as visual model inventory records or equivalent provider metadata.

#### Scenario: Refresh ComfyUI inventory
- **Given** a ComfyUI provider is configured
- **When** model inventory is refreshed
- **Then** available checkpoint and LoRA names SHALL be recorded or selected without hardcoding local paths
- **And** metadata MAY include trigger words, compatible base models, recommended weight, style tags, character tags, visibility, and source/license notes.

#### Scenario: LoRA compatibility is checked
- **Given** a visual generation plan selects multiple LoRAs
- **When** validation runs
- **Then** the system SHALL check allowed LoRAs, banned LoRAs, base-model compatibility, recommended weights, and known conflicts before provider execution.

### Requirement: Character Visual Generation Profile
The system SHALL support per-character and worldline-scoped visual generation profiles. A profile MAY define preferred checkpoint, allowed LoRAs, default LoRAs, banned LoRAs, style prompt fragments, character prompt fragments, negative prompt fragments, reference image assets, default workflow template, expression workflow template, CG workflow template, pose policy, and outfit policy.

#### Scenario: Character profile constrains generation
- **Given** a character has a visual generation profile
- **When** an image generation plan is created for that character
- **Then** the plan SHALL use only allowed model assets, workflow templates, prompt fragments, and reference images
- **And** the plan SHALL preserve world and worldline scope.

### Requirement: Provider-neutral Visual Generation Plan
The system SHALL create provider-neutral visual generation plans before calling provider adapters. A plan SHALL include intent, provider id, workflow template id when applicable, character ids, scene id when applicable, prompt plan, model plan, reference assets, output plan, validation results, and safe evidence refs.

#### Scenario: Plan expression variant
- **Given** a request asks for a character expression variant
- **When** the visual generation planner runs
- **Then** it SHALL produce a plan with prompt strategy, model choices, reference assets, output asset kind, workflow template choice, and validation results
- **And** provider adapters SHALL receive only the validated provider-specific request derived from that plan.

### Requirement: ComfyUI Workflow Execution Boundary
The system SHALL execute ComfyUI only through registered workflow templates and validated slots. The system SHALL NOT allow a runtime agent to generate arbitrary workflow JSON and execute it directly.

#### Scenario: Agent requests ComfyUI image generation
- **Given** an agent requests image generation and the selected provider is ComfyUI
- **When** the request is planned
- **Then** the system SHALL select a registered workflow template and fill validated slots
- **And** the final workflow SHALL be validated before execution
- **And** all outputs SHALL be written through media assets and media objects.

#### Scenario: Agent provides raw workflow JSON
- **Given** a runtime agent response contains raw ComfyUI workflow JSON
- **When** execution is requested
- **Then** the system SHALL reject direct execution
- **And** it MAY convert safe intent into a reviewable proposal instead.

### Requirement: AI-assisted Workflow Personalization
The system MAY let AI propose workflow bindings, character visual generation profiles, or workflow variants during world creation. These proposals SHALL be reviewable, validated, versioned, and explicitly applied before activation. They SHALL NOT execute automatically.

#### Scenario: AI proposes character generation profile
- **Given** a world creation process has imported character assets and source context
- **When** AI proposes a character-specific generation profile
- **Then** the proposal SHALL record checkpoint, LoRA, workflow template, prompt, negative prompt, reference image, pose, outfit, and style recommendations
- **And** an admin SHALL review/apply the proposal before it becomes active.

#### Scenario: AI proposes workflow variant
- **Given** AI proposes a workflow variant based on an existing template
- **When** the proposal is reviewed
- **Then** only whitelisted node or parameter changes SHALL be allowed
- **And** schema, capability, slot, and provider validation SHALL pass before apply.

### Requirement: Cross-provider Image Control
The system SHALL express prompt strategy, reference images, output intent, composition, and model choices in a provider-neutral form. Provider adapters SHALL map the plan to ComfyUI, Z-Image, GPT Image, OpenAI-compatible image, or generic image API requests.

#### Scenario: Execute Z-Image plan
- **Given** the selected provider is Z-Image
- **When** an image plan is executed
- **Then** the adapter SHALL map the provider-neutral prompt and output plan to the Z-Image request format
- **And** unsupported workflow, LoRA, edit, or reference fields SHALL be rejected or ignored according to capability validation.

#### Scenario: Execute GPT Image plan with references
- **Given** the selected provider is GPT Image and the plan includes reference images
- **When** the image plan is executed
- **Then** the adapter SHALL map allowed reference images to the provider request format
- **And** each reference image SHALL pass media visibility, role, world, and worldline checks.

### Requirement: Safety and Traceability
The system SHALL preserve safe traceability for visual generation plans and executions, including world id, worldline id, character id when applicable, provider id, workflow template id when applicable, source reference assets, resulting media assets, model invocation link when provider-backed, and prompt snapshot where applicable.

#### Scenario: Inspect visual generation evidence
- **Given** a generated visual asset exists
- **When** an admin inspects generation evidence
- **Then** the system SHALL show safe plan, provider, workflow, model, reference asset, invocation, and resulting media refs
- **And** reader/player/member APIs SHALL NOT expose local model paths, storage paths, raw workflow JSON, raw prompts, raw outputs, bytes, base64, or resolved secrets.
