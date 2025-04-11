# VPC Detective - Enhancement TODO List

This document tracks planned enhancements for the VPC Detective tool to provide more comprehensive VPC infrastructure reporting.

## Priority 1 - Core Network Information

- [ ] **VPC Flow Logs Status**
  - Add detection of whether VPC Flow Logs are enabled
  - Include destination (CloudWatch Logs, S3, or Firehose)
  - Show retention period configuration

- [ ] **VPC Peering Connections**
  - List active VPC peering connections
  - Show peer VPC ID and account information
  - Display status of each peering connection

- [ ] **Transit Gateway Attachments**
  - Detect if VPC is attached to any Transit Gateways
  - Include Transit Gateway ID and attachment ID
  - Show route table associations

- [ ] **Route Tables**
  - Count route tables per VPC
  - Summarize routing configurations (internet routes, local routes)
  - Flag routes to 0.0.0.0/0 (internet access)

## Priority 2 - Security Information

- [ ] **Security Groups**
  - Count security groups per VPC
  - Highlight security groups with public access (0.0.0.0/0)
  - Show unused security groups

- [ ] **Network ACLs**
  - Count custom NACLs
  - Highlight NACLs with public access rules
  - Show subnet associations

- [ ] **VPC Endpoints**
  - Count and list types of VPC endpoints (Gateway, Interface)
  - Show services accessed via endpoints (S3, DynamoDB, etc.)
  - Display security groups associated with interface endpoints

## Priority 3 - Governance & Cost

- [ ] **Cost Information**
  - Estimate NAT Gateway costs (monthly)
  - Calculate VPC Endpoint costs
  - Show other billable VPC resources

## Priority 5 - Additional Metadata

- [ ] **Last Modified Date**
  - Track when the VPC or key components were last modified
  - Show creation date

## Documentation Updates

- [ ] Update README.md with new features
- [ ] Update example output in documentation
- [ ] Document new permissions required for additional API calls
- [ ] Create a sample report with all features enabled
