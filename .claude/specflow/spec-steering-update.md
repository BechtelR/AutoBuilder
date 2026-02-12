# Spec Steering Update Command

Update existing steering documents with fresh codebase analysis while preserving valuable accurate content. Use subagents to assist your work and preserve your context window.

## Usage
```
/spec-steering-update
```

## Instructions
You are updating the project steering documents that guide all future spec development. This command performs a **thorough, comprehensive codebase review** (same as setup) but **intelligently merges** findings with existing documents to preserve valuable accurate content while updating outdated information and adding new insights.

## Key Difference from Setup
**Setup** creates from scratch. **Update** performs full analysis but preserves accurate content while updating/adding new findings.

## Process

1. **Load Existing Steering Documents**
   - Load current steering context:
     .claude/steering/*.md

   - Parse and store existing content from:
     - product.md
     - roadmap.md
     - standards.md
     - structure.md
     - tech.md
   - If any documents are missing, note which ones need to be created
   - Display summary of what currently exists

2. **Search for Standards and Analyze Project Thoroughly**
   - **CRITICAL**: Perform comprehensive codebase review (same depth as setup)
   - Look for: `CONTRIBUTING.md`, `STANDARDS.md`, `CONVENTIONS.md`, `STYLE_GUIDE.md`, `DEVELOPMENT.md`, config files (`.editorconfig`, `.prettierrc`, `.eslintrc*`), files in `.claude/`, `.dev/`, `docs/` containing "standard", "convention", "rule", or "guideline"
   - Look for: `package.json`, `requirements.txt`, `go.mod`, README files, configuration files
   - Extract from found files: Tech stack, directory structure, coding patterns, features, coding style, UX preferences, architecture patterns, testing requirements

3. **Compare Findings Against Existing Documents**
   - **CRITICAL**: Compare fresh analysis with existing steering docs and categorize:
     - **✅ ACCURATE**: Matches codebase → Preserve unchanged
     - **🔄 OUTDATED**: Contradicts codebase → Update (show old → new)
     - **➕ NEW**: Found in codebase but not documented → Add
     - **📝 ENHANCED**: Accurate but can be expanded → Expand with context

4. **Present Comparison and Fill Gaps**
   - Present comparison for each document (product.md, roadmap.md, tech.md, structure.md, standards.md):
     - ✅ ACCURATE sections (will preserve)
     - 🔄 OUTDATED items (will update with old → new)
     - ➕ NEW content (will add)
     - 📝 ENHANCED sections (will expand)
   - Ask: "Do these findings look correct? Should I preserve ACCURATE and update OUTDATED?"
   - Ask: "Any other rules, standards, or conventions I should know?"
   - Fill gaps with targeted questions:
     - **Product**: What problem does this solve? Unique advantages? Primary users? Business objectives? Success metrics?
     - **Technology**: Technical constraints? Third-party services? Performance requirements?
     - **Structure**: How should new features be organized? Testing requirements?
     - **Standards**: Mandatory code patterns/anti-patterns? Code review requirements? Security/compliance standards?

5. **Archive Existing Steering Documents**
   - **CRITICAL**: Before making ANY changes, archive current steering documents
   - Create: `.claude/steering/.archive/YYMMDD/` (e.g., 251002 for Oct 2, 2025)
   - Copy all docs: `product.md`, `roadmap.md`, `tech.md`, `structure.md`, `standards.md` to archive
   - Add `(DEPRECATED)` to first line of each archived document
   - Confirm to user: "Backed up to `.claude/steering/.archive/251002/` and marked DEPRECATED"
   - **Note**: If user specifies version (e.g., "v2.1"), use instead: `.claude/steering/.archive/v2.1/`

6. **Generate Merged Steering Documents**
   - Create `.claude/steering/` directory if it doesn't exist
   - Generate **five** merged documents with version header
   - **Version header**: `*Version: MAJOR.YYMM.BUILD.PATCH*` on second line (ask user or default to `1.YYMM.1.0`)
     ```markdown
     # Product Context
     *Version: 1.2510.1.0*
     ```
   - **For each document**:
     - **product.md**: Product vision, users, strategic advantages, features, objectives
     - **roadmap.md**: High-level roadmap structure, phase overview, terminology, risks. **DO NOT include current development status** (completion percentages, active tasks, etc.) - refer to `.dev/01-ROADMAP.md` as the master document for current status
     - **tech.md**: Technology stack, tools, constraints, decisions
     - **structure.md**: High-level blueprint, file organization, naming conventions, patterns
     - **standards.md**: Engineering standards, coding rules, patterns (keep focused and concise)
   - **Merging strategy**:
     - Preserve ✅ ACCURATE sections unchanged
     - Update 🔄 OUTDATED sections with current info (show old → new)
     - Add ➕ NEW sections in appropriate locations
     - Enhance 📝 ENHANCED sections with insights (when beneficial)

7. **Review and Confirm**
   - Ensure standards.md is focused and concise (essential rules only, no redundancy with tech.md/structure.md)
   - Present merged documents and highlight what changed (preserved vs. updated vs. new)
   - Get approval, make adjustments

## Important Notes

- Perform complete codebase review (same depth as setup command)
- Never lose valuable accurate content - preservation is critical
- Intelligently merge existing docs with fresh findings
- Update confidently - replace outdated info with current codebase state
- Steering documents are persistent and referenced in all spec commands
- Keep focused - each document covers its specific domain
- Update regularly - steering docs should evolve with the project
- Never include sensitive data (passwords, API keys, credentials)

## Next Steps
After steering documents are updated, they will automatically be referenced during:
- `/spec-create` - Align requirements with product vision
- `/spec-update` - Update existing specs with current steering context
- `/spec-tasks-rebuild` - Rebuild tasks following current conventions
- `/spec-execute` - Implement following all conventions
