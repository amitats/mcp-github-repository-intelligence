# Claude Desktop Repository Analysis – Prompt and Sample Result

This document captures the Claude Desktop prompt used with the **MCP-Driven GitHub Repository Intelligence Platform** and a sample repository-analysis result produced through the automation.

The purpose is to show how a user can provide a GitHub repository URL in Claude Desktop, request a complete technical analysis in normal English, and have Claude use the MCP repository-intelligence tooling to analyze the repository and return structured technical findings.

---

## 1. Claude Desktop Prompt

```text
Analyze this GitHub repository and give me a complete technical analysis:

https://github.com/<project>/partner-provisioning-adapter.git

I want the full repository analysis, not a short summary.

First analyze the repository if it has not already been analyzed, then use the generated repository intelligence to explain:

- What the repository/application does
- Complete technology stack
- Repository structure and important files
- Main components and their responsibilities
- Complete code architecture
- Component/package/module relationships
- Application entry points
- Startup and initialization flow
- Complete end-to-end code flow
- Detailed static code flows detected in the source
- Important functions, methods and source files involved
- API endpoints and their code flow
- Handler → service/usecase → repository → DAL/client flow where applicable
- Database operations where applicable
- External API and integration calls
- Dependencies and compatibility information

For detected dependencies, retrieve current compatibility information through the configured MCP compatibility service, including the detected/current version, latest stable version, compatibility/update status, and the external source used. Do not guess compatibility or version information.

Also include:

- Tests, testing frameworks and actual coverage information if available
- Configuration, Docker, Kubernetes, Helm, Terraform and CI/CD details where detected
- Main application use cases
- Shutdown/runtime flow where applicable
- Any analysis limitations

For code flows, show the actual sequence from entry point through the relevant components/functions and include source file names wherever available.

Use the repository analysis as the source of truth. Do not invent missing functions, relationships, APIs, coverage values, or code flows.

Give me the complete detailed technical result rather than only an executive summary.
```

---

## 2. Sample Claude Desktop Result

### Repository

`partner-provisioning-adapter`

The repository had not previously been analyzed, so Claude triggered repository analysis through the configured MCP tooling.

The analysis scanned **652 files**. The local LLM semantic pass was skipped, so the result was primarily based on deterministic repository analysis.

---

## 3. Application Purpose

The repository documentation identifies the application as **PPA – Partner Provisioning Adapter**.

The analysis found evidence that the service:

- Runs locally through Docker Compose.
- Targets Java 21.
- Uses DynamoDB for local persistence.
- Contains partner integrations for Boku and HBO.
- Handles partner entitlement and provisioning operations.
- Contains Kafka-related components.
- Includes activation, account-state and partner-product functionality.

Some higher-level functional interpretation was based on repository structure, configuration and naming where the deterministic analyzer did not produce an explicit semantic result.

---

## 4. Technology Stack

| Area | Detected information |
|---|---|
| Languages | Java, Shell |
| Runtime | Java 21 |
| Database | DynamoDB evidence present |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Kubernetes | Not detected |
| Helm | Not detected |
| Terraform | Not detected |
| Testing | Cucumber/BDD and test-source evidence present |
| External integrations | Boku and HBO evidence present |
| Messaging | Kafka-related packages and configuration present |

The analyzer did not explicitly populate its framework field. Repository evidence appeared consistent with Spring-style application structure, but this was not presented as a tool-confirmed framework result.

---

## 5. Repository Structure

The analysis scanned **652 files**.

Major areas included:

| Directory | Files |
|---|---:|
| `service` | 448 |
| `config` | 95 |
| `ppa-bruno` | 30 |
| `.github` | 24 |
| `stubs` | 9 |
| `.applications` | 9 |
| `spec` | 6 |
| `gradle` | 3 |
| `certificate-checker` | 3 |
| `commons` | 3 |
| `jumpbox` | 2 |
| `kafka` | 2 |
| `dynamodb` | 1 |
| `.jira` | 1 |

The file scan included Java source, JSON, YAML, Gradle files, shell scripts, Cucumber feature files, Markdown documentation, certificates and configuration artifacts.

Important artifacts included:

- `README.md`
- `docker-compose.yaml`
- `service/Dockerfile`
- `service/nft/Dockerfile`
- `sas-openapi.json`
- GitHub Actions workflow files
- application configuration
- Kafka configuration and certificates
- Boku/HBO stub mappings
- Gradle deployment plugins

---

## 6. Main Components

The deterministic scan identified 14 major repository areas:

- `service` – primary application source and tests
- `config` – runtime/integration configuration
- `ppa-bruno` – Bruno API collections
- `.github` – CI/CD workflows
- `stubs` – mock/stub definitions
- `.applications` – application/deployment manifests
- `spec` – specification and API contract files
- `gradle` – build tooling
- `certificate-checker` – certificate validation utility
- `commons` – shared code
- `jumpbox` – jumpbox-related tooling
- `kafka` – Kafka assets
- `dynamodb` – DynamoDB initialization assets
- `.jira` – Jira-related configuration

Within the Java service, source paths showed controller, service, database, repository, HTTP client, Kafka, security, filter, exception, health, metrics, validation, configuration, domain and utility areas.

---

## 7. Architecture Analysis

The analyzer classified the repository as having a:

> Modular repository architecture

The deployment model was detected as Docker.

The analysis also found Gradle-based deployment customization for multiple deployment environments/regions.

However, the deterministic analysis reported:

- 0 repository-local dependency relationships
- 0 executable/package entry points
- no generated Java call graph

Therefore, the result deliberately avoided presenting unverified component relationships as facts.

---

## 8. Application Entry Point and Startup Flow

No executable application entry point was positively detected by the analyzer.

Although repository evidence suggested a runnable Java service, the result did not invent a `main()` entry point that had not been surfaced by the analysis.

The deterministic startup-flow output identified runtime configuration loading as a startup activity.

It detected configuration such as:

- application YAML
- Jira configuration
- HBO key material
- Kafka keystores/truststores
- integration configuration

No complete verified startup call sequence was produced.

---

## 9. Detailed Code Flow

The `detailed_static_code_flows` result was empty for this analysis.

As a result, the automation did not claim to have proven a complete:

```text
Controller
    ↓
Service / Use Case
    ↓
Repository
    ↓
DAL / Client
    ↓
Database / External System
```

chain.

Potentially relevant classes were visible from repository structure, but they were not presented as a verified caller-to-callee sequence when the analyzer had not established those edges.

---

## 10. Important Source Areas

The result identified source files/classes associated with several technical areas.

### Controllers

- `ExternalController`
- `InternalController`
- `ProvisionedPartnerInternalController`

### Services

- `ActivationUrlService`
- `CancelEntitlementService`
- `EntitlementPersistenceService`
- `JwksService`
- `PartnerEntitlementStateService`
- `PartnerInteractionHelper`
- `PartnerProductPersistenceService`
- `ProvisionEntitlementService`
- `ProvisionedPartnerInternalService`
- `AccountDeleteService`

### HTTP Clients

- `BokuClient`
- `BokuClientService`
- `HboClientService`
- `HBOEventClient`
- `HBOCompleteClient`

### Database

- `ProvisionedPartnerProductRepository`
- `MultiDynamoClientProvider`
- `PpaTableResolverConfig`
- `SortKeyBuilder`

### Kafka

The analysis found producer, sender, event-service, validation, callback and topic utility components.

### Security

The repository contained signature utilities/services, incoming/outgoing signature filters and user-security components.

### Health

Health-check components were found for Boku, HBO, DynamoDB and Kafka.

---

## 11. API Analysis

Four API-style definitions were surfaced:

| Method | Endpoint | Component |
|---|---|---|
| GET | `/household/{householdId}` | `ProvisionedPartnerInternalController` |
| GET | `/external-account/{externalAccountId}` | `ProvisionedPartnerInternalController` |
| POST | `/integration-api/v2/event/{partnerId}` | `HBOEventClient` |
| GET | `/broker/complete/{partnerId}/{brandId}` | `HBOCompleteClient` |

The analysis noted that the HBO client entries appear to represent outbound calls rather than endpoints exposed by PPA.

Because handler bodies and verified call relationships were not extracted, the automation did not invent an endpoint-to-database call sequence.

---

## 12. Database Analysis

DynamoDB was supported by repository documentation and source structure.

Database-related areas included configuration, providers, repositories and utility classes.

However, explicit source-level CRUD calls tied to a verified execution flow were not extracted during this analysis pass.

---

## 13. External Integrations

The dedicated external-call field was empty.

Other repository evidence indicated integrations with:

- Boku
- HBO

The repository contained client packages and extensive stub mappings for partner operations and success/failure scenarios.

These were therefore described as evidence-supported integrations rather than falsely presented as fully traced external call sites.

---

## 14. Dependencies and Compatibility

The dependency extraction returned no structured dependency records even though Gradle files were present.

Because no reliable package/version pairs were extracted, the MCP compatibility lookup was not given guessed dependencies.

This meant that:

- detected dependency versions were unavailable;
- latest-version comparisons could not be reliably performed;
- compatibility status was not invented.

This behavior demonstrates the evidence-first rule used by the automation.

---

## 15. Tests and Coverage

The analyzer detected **182 test files**.

Repository evidence included:

- Cucumber/BDD functional tests
- `.feature` files
- WireMock-style integration stubs
- Java unit-test sources
- controller tests
- service tests
- database tests
- Kafka tests
- HTTP-client tests
- security/filter tests

No actual coverage percentage was found.

The result therefore reported coverage as unavailable instead of estimating a percentage.

---

## 16. Docker, Infrastructure and CI/CD

### Docker

Detected:

- `docker-compose.yaml`
- `service/Dockerfile`
- `service/nft/Dockerfile`

### Kubernetes

Not detected.

### Helm

Not detected.

### Terraform

Not detected.

### CI/CD

The repository contained **19 GitHub Actions workflows**, covering application/service deployment, testing, certificate checking, Kafka, jumpbox operations, retries, PR automation and environment/tenant-specific deployment processes.

---

## 17. Main Application Use Cases

The dedicated semantic use-case field was empty because the local LLM semantic stage had been skipped.

Functional-test names nevertheless provided repository evidence for areas including:

- entitlement creation
- entitlement update
- entitlement cancellation
- activation URL handling
- HBO-specific entitlement operations
- event processing
- account cleanup
- activation-status checks
- JWKS retrieval
- multi-credential handling
- health and metrics endpoints

These were reported based on repository evidence rather than generated assumptions.

---

## 18. Shutdown and Runtime Flow

No explicit shutdown flow was detected.

The analyzer did not surface shutdown hooks or lifecycle-listener code as part of its generated execution flow.

Therefore, no shutdown sequence was invented.

---

## 19. Analysis Limitations

This run exposed several limitations of the current deterministic analysis:

1. The local semantic LLM stage was skipped.
2. No executable Java entry point was detected.
3. Java-specific function/method call-graph extraction was not available in this result.
4. Repository-local call relationships were not detected.
5. Detailed static code flows were empty.
6. Gradle dependencies were not converted into structured dependency/version records.
7. Compatibility lookup could therefore not run against verified dependencies.
8. Some framework/database/testing fields remained empty despite supporting repository evidence.
9. No actual test-coverage percentage was available.
10. Some integration and functional conclusions could only be reported as supporting evidence rather than fully traced execution paths.

These limitations were explicitly surfaced instead of filling missing information with assumptions.

---

## 20. What This Demonstrates

This test shows the intended MCP-driven workflow:

```text
GitHub Repository URL
        ↓
Claude Desktop
        ↓
Repository Intelligence MCP Tool
        ↓
Repository Ingestion and Scanning
        ↓
Static Repository Analysis
        ↓
Structured Repository Intelligence
        ↓
Compatibility MCP Lookup where reliable versions exist
        ↓
Claude Desktop
        ↓
Detailed Natural-Language Technical Analysis
```

The important design principle is that **repository facts come from repository analysis**.

Claude acts as the conversational interface over the generated intelligence. When the analyzer cannot prove a relationship, dependency, code flow, coverage value or integration detail, the result should clearly identify that limitation rather than inventing missing technical information.

---

## Summary

The Claude Desktop prompt requests a complete repository analysis covering application purpose, technology stack, repository structure, architecture, components, entry points, code flows, APIs, database operations, integrations, dependencies, compatibility, tests, infrastructure, CI/CD, use cases and limitations.

In this sample run, the MCP-driven automation successfully scanned and classified a large Java repository and returned substantial structured information. It also exposed gaps in the current deterministic analyzer, particularly around Java call-graph analysis, Gradle dependency extraction and detailed end-to-end static flow tracing.

Those gaps are retained in the result because the platform is designed to distinguish **verified repository evidence** from **inference or unavailable information**.
