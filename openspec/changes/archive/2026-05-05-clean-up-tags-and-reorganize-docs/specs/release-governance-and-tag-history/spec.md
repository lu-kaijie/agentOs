## ADDED Requirements

### Requirement: Repository SHALL maintain a canonical tag history map
The repository SHALL provide a canonical, human-readable mapping that explains each maintained release tag, the commit it points to, the milestone or change stage it represents, and the major capability introduced at that point.

#### Scenario: Maintainer checks historical releases
- **WHEN** a maintainer opens the release history documentation
- **THEN** they MUST be able to see which tag maps to which commit and what that tag represents

### Requirement: Historical tags SHALL be corrected to a self-consistent release sequence
The repository SHALL correct duplicated, missing, or misaligned historical tags so that the maintained tag sequence is self-consistent and matches the documented release history.

#### Scenario: Duplicate tag targets are found
- **WHEN** historical inspection shows multiple tags incorrectly pointing to the same milestone commit
- **THEN** the repository MUST either remap or remove the incorrect duplicates and preserve a single documented interpretation for each release point

#### Scenario: A missing release tag is identified
- **WHEN** the documented milestone sequence includes a release that does not currently exist as a git tag
- **THEN** the repository MUST create the missing tag and record it in the canonical mapping

### Requirement: Tag cleanup SHALL include explicit verification rounds
The repository SHALL define and execute at least two verification rounds after tag cleanup: one round for git tag correctness and one round for documentation consistency.

#### Scenario: Tag cleanup is complete
- **WHEN** tag rewrite operations finish
- **THEN** the maintainer MUST verify the final tag-to-commit mapping against the planned mapping table

#### Scenario: Documentation is updated after tag cleanup
- **WHEN** release history and milestone documentation are regenerated
- **THEN** the maintainer MUST perform a second verification round to confirm the docs match the actual git tags and links
