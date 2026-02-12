<!--
DOMAIN-SPECIFIC GUIDANCE:
- Apps: Focus on user features, setup, development server, UI components
- Services: Emphasize API endpoints, health checks, configuration, data flow
- Packages: Highlight installation, exports, usage examples, dependencies
- Components: Show component usage, props, theming, accessibility
-->

# [DOMAIN NAME]

[Brief description of what this component/service does and its purpose]

## Overview

[One paragraph explaining the domain's role, key features, and value proposition]

## Quick Start

### Prerequisites
- [Language and version]
- [Package manager]
- [Other prerequisites]

### Installation
```bash
# Install dependencies
[INSTALL_COMMAND]

# [Domain-specific setup commands]
[SETUP_COMMAND]
```

### Development
```bash
# Start development server
[DEV_COMMAND]

# Run tests
[TEST_COMMAND]

# Build
[BUILD_COMMAND]
```

## Features

- **[Feature 1]**: [Brief description]
- **[Feature 2]**: [Brief description]
- **[Feature 3]**: [Brief description]

## Architecture

[Brief architectural overview - link to BLUEPRINT.md for details]

**Type**: [App/Service/Package]
**Technology**: [Primary framework/language]
**Dependencies**: [Key dependencies]

## Configuration

### Environment Variables
```bash
# [Environment variable descriptions]
VARIABLE_NAME=value
```

### Development URLs
- **Local**: [Development URL]
- **Health Check**: [Health check endpoint]
- **Storybook**: [Component library URL] (for UI packages)
- **Admin Interface**: [Management interface] (for services)

## Usage Examples

### [For Services - API Endpoints]
```
# Core endpoints
GET  /api/v1/[resource]
POST /api/v1/[resource]
```

### [For Packages - Imports and Usage]
```
# Main exports
import { MainExport } from '[PACKAGE_NAME]';

# Usage examples
const example = new MainExport();
```

### [For Apps - Key Features]
```
# Core components or features
import { Component } from './components';
```

## Testing

```bash
# Run all tests
[TEST_COMMAND]

# Run specific test types
[UNIT_TEST_COMMAND]
[INTEGRATION_TEST_COMMAND]
```

## Deployment

[Brief deployment instructions or link to deployment docs]

## Troubleshooting

### Common Issues

**[Specific Issue Name]**: [One sentence problem description]
- **Solution**: [Specific steps to resolve]

**[Another Common Issue]**: [Problem description]
- **Solution**: [Resolution steps with commands if applicable]

### Debug Commands
```bash
# [Debug command and purpose]
[DEBUG_COMMAND]
```

## Contributing

See [AGENTS.md](./AGENTS.md) for development guidelines and coding standards.

## Documentation

- **[AGENTS.md](./AGENTS.md)**: Development workflow and commands
- **[BLUEPRINT.md](./BLUEPRINT.md)**: Technical architecture and design
- **[docs/](./docs/)**: Additional documentation (if applicable)
- **[Related Components]**: Links to related package documentation

### External Resources (if applicable)
- **[Technology Documentation](https://...)**: Framework/library docs
- **[Vendor Documentation](https://...)**: Third-party service docs

## Security

[Brief security considerations relevant to this domain]

- **Sensitive Data**: [How sensitive data is handled if applicable]
- **Access Control**: [Authentication/authorization approach]
- **Data Protection**: [Key security measures]

## Support

For questions or issues:
- Check the troubleshooting section above
- Review [AGENTS.md](./AGENTS.md) for development guidelines
- Consult [BLUEPRINT.md](./BLUEPRINT.md) for architectural details

---

*Part of the [ProjectName](../../README.md) platform*
