# API Request Lifecycle — Sequence Diagram

Traces a single authenticated API request from the browser through every layer:
CDN, load balancer, API gateway, auth, business logic, cache, database, and
back — including error handling and cache miss/hit paths.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser
    participant CDN
    participant LB as Load Balancer
    participant GW as API Gateway
    participant Auth as Auth Service
    participant Cache as Redis Cache
    participant API as Order Service
    participant DB as PostgreSQL
    participant Queue as Kafka

    User->>Browser: Click "Place Order"
    Browser->>CDN: POST /api/v1/orders
    CDN->>LB: Forward (cache miss)
    LB->>GW: Route to upstream

    GW->>Auth: Validate JWT token
    Auth->>Auth: Verify signature + expiry

    alt Token valid
        Auth-->>GW: 200 OK (user context)
    else Token expired
        Auth-->>GW: 401 Unauthorized
        GW-->>Browser: 401 — redirect to login
    end

    GW->>Cache: Check idempotency key
    alt Duplicate request
        Cache-->>GW: Return cached response
        GW-->>Browser: 200 (cached)
    else New request
        Cache-->>GW: Cache miss
        GW->>API: CreateOrder(payload)
        API->>DB: BEGIN TRANSACTION
        API->>DB: INSERT INTO orders
        API->>DB: UPDATE inventory (decrement)
        API->>DB: COMMIT

        alt DB commit success
            DB-->>API: OK
            API->>Queue: Publish OrderCreated event
            Queue-->>API: ACK
            API->>Cache: Store idempotency result (TTL 24h)
            API-->>GW: 201 Created {order_id}
            GW-->>Browser: 201 Created
            Browser-->>User: Show confirmation
        else DB error (stock insufficient)
            DB-->>API: ROLLBACK
            API-->>GW: 409 Conflict
            GW-->>Browser: 409 — item out of stock
            Browser-->>User: Show error toast
        end
    end
```
