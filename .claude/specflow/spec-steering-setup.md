# Spec Steering Setup Command

Create or update steering documents that provide persistent project context.

## Usage
```
/spec-steering-setup
```

## Instructions
You are setting up steering documents that will guide all future spec development. These documents provide persistent context about the product vision, blueprint, features, technology stack, and project structure.

## Process

1. **Check for Existing Steering Documents**
   - Look for `.claude/steering/` directory
   - Check for existing product.md, roadmap.md, tech.md, structure.md, standards.md files
   - If they exist, load and display current content
   - Check for other helpful product documents and folders:
     `mission.md`, `vision.md`, `blueprint.md`, `architecture.md`, `tech-stack`
   - If found, extract all useful design knowledge needed that a professional engineer would need to onboard the project 

2. **Search for Standards and Analyze Project**
   - Look for: `CONTRIBUTING.md`, `STANDARDS.md`, `CONVENTIONS.md`, `STYLE_GUIDE.md`, `DEVELOPMENT.md`, config files (`.editorconfig`, `.prettierrc`, `.eslintrc*`), files in `.claude/`, `.dev/`, `docs/` containing "standard", "convention", "rule", or "guideline"
   - Look for: `package.json`, `requirements.txt`, `go.mod`, README files, configuration files
   - Extract from found files: Tech stack, directory structure, coding patterns, features, coding style, UX preferences, architecture patterns, testing requirements

3. **Present and Validate Findings**
   - Present inferred details: Product (purpose, vision, features, users), Technology (frameworks, libraries, tools), Structure (organization, naming), Standards (coding rules, patterns)
   - Ask: "Do these look correct? Anything to keep or discard?"
   - Ask: "Any other rules, standards, or conventions I should know?"

4. **Fill Gaps**
   - Ask targeted questions based on user feedback to fill missing details:
     - **Product**: What problem does this solve? Unique advantages? Primary users? Business objectives? Success metrics?
     - **Technology**: Technical constraints? Third-party services? Performance requirements?
     - **Structure**: How should new features be organized? Testing requirements?
     - **Standards**: Mandatory code patterns/anti-patterns? Code review requirements? Security/compliance standards?

5. **Generate Steering Documents**
   - Create `.claude/steering/` directory if it doesn't exist
   - Generate **five** files based on templates and gathered information
   - **Version header**: `*Version: MAJOR.YYMM.BUILD.PATCH*` on second line (ask user or default to `1.YYMM.1.0`)
     ```markdown
     # Product Context
     *Version: 1.2510.1.0*
     ```
   - **For each document**:
     - **product.md**: Product vision, users, strategic advantages, features, objectives
     - **roadmap.md**: High-level roadmap structure, phase overview, terminology, risks. **DO NOT include current development status** (completion percentages, active tasks, etc.) - refer to `.dev/08-ROADMAP.md` as the master document for current status
     - **tech.md**: Technology stack, tools, constraints, decisions
     - **structure.md**: High-level blueprint, file organization, naming conventions, patterns
     - **standards.md**: Engineering standards, coding rules, patterns (keep focused and concise)

6. **Review and Confirm**
   - Ensure standards.md is focused and concise (essential rules only, no redundancy with tech.md/structure.md)
   - Present documents, get approval, make adjustments

## Important Notes

- Steering documents are persistent and referenced in all spec commands
- Keep focused - each document covers its specific domain
- Update regularly - steering docs should evolve with the project
- Never include sensitive data (passwords, API keys, credentials)

## Next Steps
After steering documents are created, they will automatically be referenced during:
- `/spec-create` - Align requirements with product vision
- `/spec-update` - Update existing specs with current steering context
- `/spec-tasks-rebuild` - Rebuild tasks following current conventions
- `/spec-execute` - Implement following all conventions
