# Requirements Document

## Introduction

This feature adds VPC Flow Logs detection capabilities to the VPC Detective tool. VPC Flow Logs are critical for network monitoring, security analysis, and compliance requirements. By detecting and reporting on Flow Logs configuration across all VPCs, administrators can quickly identify gaps in their logging coverage and ensure proper network monitoring is in place.

The enhancement will extend the existing VPC reporting functionality to include Flow Logs status, destination configuration, and retention settings, providing a comprehensive view of network logging posture across multi-account AWS environments.

## Requirements

### Requirement 1

**User Story:** As an AWS administrator, I want to see VPC Flow Logs status for each VPC in my infrastructure report, so that I can identify VPCs that lack proper network monitoring.

#### Acceptance Criteria

1. WHEN the VPC Detective tool scans a VPC THEN it SHALL check for active VPC Flow Logs configurations
2. WHEN a VPC has Flow Logs enabled THEN the system SHALL display "Enabled" in the Flow Logs status column
3. WHEN a VPC has no Flow Logs configured THEN the system SHALL display "Disabled" in the Flow Logs status column
4. WHEN a VPC has multiple Flow Logs configurations THEN the system SHALL display "Multiple" in the Flow Logs status column

### Requirement 2

**User Story:** As a security engineer, I want to see where VPC Flow Logs are being sent (CloudWatch, S3, or Kinesis), so that I can verify logs are going to the correct destinations for our security monitoring.

#### Acceptance Criteria

1. WHEN Flow Logs are enabled for a VPC THEN the system SHALL identify the destination type (CloudWatch Logs, S3, or Kinesis Data Firehose)
2. WHEN the destination is CloudWatch Logs THEN the system SHALL display "CloudWatch" as the destination
3. WHEN the destination is S3 THEN the system SHALL display "S3" as the destination
4. WHEN the destination is Kinesis Data Firehose THEN the system SHALL display "Kinesis" as the destination
5. WHEN multiple Flow Logs exist with different destinations THEN the system SHALL display all unique destination types separated by commas

### Requirement 3

**User Story:** As a compliance officer, I want to see Flow Logs retention settings, so that I can ensure we meet our data retention requirements for audit purposes.

#### Acceptance Criteria

1. WHEN Flow Logs destination is CloudWatch Logs THEN the system SHALL retrieve and display the log group retention period
2. WHEN the retention period is set THEN the system SHALL display the retention in days (e.g., "30 days", "90 days")
3. WHEN the retention period is "Never Expire" THEN the system SHALL display "Never"
4. WHEN Flow Logs destination is S3 or Kinesis THEN the system SHALL display "N/A" for retention
5. WHEN multiple Flow Logs exist with different retention periods THEN the system SHALL display the shortest retention period

### Requirement 4

**User Story:** As an AWS administrator, I want the Flow Logs information integrated into the existing VPC report format, so that I can see all VPC information in one consolidated view.

#### Acceptance Criteria

1. WHEN generating the markdown report THEN the system SHALL add Flow Logs columns to the existing VPC table
2. WHEN displaying Flow Logs information THEN the system SHALL add three new columns: "Flow Logs", "Destination", and "Retention"
3. WHEN a VPC has no Flow Logs THEN the system SHALL display "-" in the Destination and Retention columns
4. WHEN the report is generated THEN the system SHALL maintain the existing table formatting and readability

### Requirement 5

**User Story:** As a DevOps engineer, I want the tool to handle Flow Logs API errors gracefully, so that a single Flow Logs permission issue doesn't break the entire VPC scanning process.

#### Acceptance Criteria

1. WHEN the system encounters an Access Denied error for Flow Logs APIs THEN it SHALL log the error and continue processing other VPCs
2. WHEN Flow Logs API calls fail THEN the system SHALL display "Error" in the Flow Logs status column
3. WHEN Flow Logs data cannot be retrieved THEN the system SHALL display "-" in the Destination and Retention columns
4. WHEN API rate limits are encountered THEN the system SHALL implement appropriate retry logic with exponential backoff

### Requirement 6

**User Story:** As an AWS administrator, I want to see a summary of Flow Logs coverage across all my accounts, so that I can quickly assess my overall network monitoring posture.

#### Acceptance Criteria

1. WHEN the report is generated THEN the system SHALL include a summary section showing Flow Logs statistics
2. WHEN calculating statistics THEN the system SHALL count total VPCs, VPCs with Flow Logs enabled, and VPCs without Flow Logs
3. WHEN displaying the summary THEN the system SHALL show the percentage of VPCs with Flow Logs enabled
4. WHEN multiple accounts are scanned THEN the system SHALL provide both per-account and overall statistics