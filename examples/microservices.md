# E-Commerce Microservices Platform

A production-grade e-commerce architecture with 20+ services, showing the full
request path from browser through CDN, load balancer, API gateway, into core
business services, event-driven pipelines, data stores, and observability.

```architecture
title: E-Commerce Platform Architecture

services:
  Web Browser
  Mobile App
  CDN Edge Network
  Load Balancer
  API Gateway
  Auth Service
  User Service
  Product Catalog
  Search Engine
  Shopping Cart
  Order Service
  Payment Gateway
  Inventory Database
  Notification Service
  Email Provider
  Redis Cache
  Kafka Event Bus
  Warehouse Service
  Analytics Dashboard
  Monitoring Stack
  CI/CD Pipeline
  Vault Secrets Manager
  Container Registry

flow:
  Web Browser -> CDN Edge Network
  Mobile App -> CDN Edge Network
  CDN Edge Network -> Load Balancer
  Load Balancer -> API Gateway
  API Gateway -> Auth Service
  Auth Service -> Vault Secrets Manager
  API Gateway -> User Service
  API Gateway -> Product Catalog
  API Gateway -> Shopping Cart
  API Gateway -> Search Engine
  Product Catalog -> Inventory Database
  Product Catalog -> Redis Cache
  Search Engine -> Redis Cache
  Shopping Cart -> Redis Cache
  Shopping Cart -> Order Service
  Order Service -> Payment Gateway
  Order Service -> Kafka Event Bus
  Kafka Event Bus -> Notification Service
  Kafka Event Bus -> Warehouse Service
  Kafka Event Bus -> Analytics Dashboard
  Notification Service -> Email Provider
  Monitoring Stack -> API Gateway
  Monitoring Stack -> Kafka Event Bus
  CI/CD Pipeline -> Container Registry
  Container Registry -> API Gateway

groups:
  Client Layer: Web Browser, Mobile App, CDN Edge Network
  Edge Services: Load Balancer, API Gateway, Auth Service
  Core Business: User Service, Product Catalog, Search Engine, Shopping Cart, Order Service
  Payment & Fulfillment: Payment Gateway, Warehouse Service, Notification Service, Email Provider
  Data & Messaging: Inventory Database, Redis Cache, Kafka Event Bus
  Platform: Monitoring Stack, Analytics Dashboard, CI/CD Pipeline, Vault Secrets Manager, Container Registry
```

## Architecture Highlights

- **Client Layer** — Browser + mobile → CDN for static assets → LB for API traffic
- **Edge** — API Gateway handles routing, rate limiting, auth token validation
- **Core** — Product catalog cached in Redis, cart sessions in Redis, orders via Kafka
- **Events** — Kafka decouples order processing: notifications, warehouse, analytics all consume independently
- **Observability** — Monitoring stack watches gateway + Kafka health; analytics dashboard for business metrics
