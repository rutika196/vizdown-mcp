# CI/CD Pipeline Architecture

Full deployment pipeline from developer push through build, test, staging,
and production deployment — showing the infrastructure that supports it.

```architecture
title: CI/CD Deployment Pipeline

services:
  Developer Workstation
  GitHub Repository
  GitHub Actions Runner
  Docker Build Server
  Container Registry
  SonarQube Scanner
  Unit Test Runner
  Integration Test Runner
  E2E Test Suite
  Staging Kubernetes
  Production Kubernetes
  Database Migration Tool
  Vault Secrets
  Monitoring Dashboard
  Slack Notifications

flow:
  Developer Workstation -> GitHub Repository
  GitHub Repository -> GitHub Actions Runner
  GitHub Actions Runner -> Docker Build Server
  Docker Build Server -> Container Registry
  GitHub Actions Runner -> SonarQube Scanner
  GitHub Actions Runner -> Unit Test Runner
  GitHub Actions Runner -> Integration Test Runner
  Container Registry -> Staging Kubernetes
  Staging Kubernetes -> E2E Test Suite
  E2E Test Suite -> Production Kubernetes
  Production Kubernetes -> Database Migration Tool
  Database Migration Tool -> Vault Secrets
  Production Kubernetes -> Monitoring Dashboard
  Monitoring Dashboard -> Slack Notifications

groups:
  Source Control: Developer Workstation, GitHub Repository
  Build & Scan: GitHub Actions Runner, Docker Build Server, Container Registry, SonarQube Scanner
  Test: Unit Test Runner, Integration Test Runner, E2E Test Suite
  Deploy: Staging Kubernetes, Production Kubernetes, Database Migration Tool
  Ops: Vault Secrets, Monitoring Dashboard, Slack Notifications
```
