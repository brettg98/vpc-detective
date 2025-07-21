# Implementation Plan

- [x] 1. Create Flow Logs data collection functions
  - Implement `get_vpc_flow_logs()` function to retrieve Flow Logs configurations for a VPC
  - Implement `get_cloudwatch_retention()` function to get CloudWatch log group retention periods
  - Add proper error handling for AWS API calls with graceful degradation
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2, 5.3, 5.4_

- [x] 2. Integrate Flow Logs detection into existing VPC data collection
  - Modify `get_vpcs()` function to call Flow Logs detection for each VPC
  - Add Flow Logs data fields to the VPC data dictionary structure
  - Ensure CloudWatch Logs client is created and managed properly
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Implement Flow Logs summary calculation functionality
  - Create `calculate_flow_logs_summary()` function to compute coverage statistics
  - Calculate total VPCs, enabled/disabled counts, and percentages
  - Generate per-account statistics for multi-account environments
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 4. Enhance markdown report generation with Flow Logs columns
  - Modify `generate_markdown()` function to include Flow Logs table columns
  - Add "Flow Logs", "Destination", and "Retention" columns to VPC tables
  - Ensure proper formatting and alignment of new columns
  - Handle display of multiple destinations and retention values
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5. Add Flow Logs summary section to markdown report
  - Extend `generate_markdown()` to include Flow Logs coverage summary
  - Display overall statistics (total VPCs, coverage percentage)
  - Include per-account breakdown of Flow Logs coverage
  - Format summary section with clear headings and statistics
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Update requirements.txt and handle new AWS permissions
  - Ensure boto3 version supports required Flow Logs and CloudWatch Logs APIs
  - Document new IAM permissions needed in code comments
  - Test graceful handling when permissions are missing
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 7. Create comprehensive unit tests for Flow Logs functionality
  - Write tests for `get_vpc_flow_logs()` with various Flow Logs configurations
  - Write tests for `get_cloudwatch_retention()` with different retention settings
  - Write tests for `calculate_flow_logs_summary()` with edge cases
  - Test error handling scenarios (access denied, API failures)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3, 5.4_

- [x] 8. Test integration with existing VPC Detective workflow
  - Test enhanced functionality with sample account configurations
  - Verify markdown report generation includes all new Flow Logs information
  - Test error handling when Flow Logs permissions are missing
  - Validate that existing functionality remains unchanged
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4_