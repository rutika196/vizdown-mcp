# Order Lifecycle — State Diagram

Complete state machine for an e-commerce order, from cart checkout through
payment processing, fulfillment, shipping, delivery, and all cancellation /
refund / dispute paths.

```mermaid
stateDiagram-v2
    [*] --> Draft : Customer adds items

    Draft --> PendingPayment : Submit order
    Draft --> Cancelled : Customer cancels

    PendingPayment --> PaymentProcessing : Payment initiated
    PendingPayment --> Cancelled : Payment timeout (30 min)

    PaymentProcessing --> PaymentFailed : Card declined / error
    PaymentProcessing --> Confirmed : Payment captured

    PaymentFailed --> PendingPayment : Retry payment
    PaymentFailed --> Cancelled : Max retries exceeded

    Confirmed --> Preparing : Warehouse picks order
    Confirmed --> Cancelled : Admin cancels (pre-fulfillment)

    Preparing --> ReadyToShip : Items packed
    Preparing --> PartiallyFulfilled : Some items unavailable

    PartiallyFulfilled --> ReadyToShip : Remaining items packed
    PartiallyFulfilled --> RefundInitiated : Customer requests partial refund

    ReadyToShip --> Shipped : Carrier picks up
    Shipped --> InTransit : Tracking update received
    InTransit --> OutForDelivery : Last mile
    OutForDelivery --> Delivered : Proof of delivery

    Delivered --> ReturnRequested : Customer initiates return (14 days)
    Delivered --> Disputed : Chargeback filed
    Delivered --> [*] : Order complete

    ReturnRequested --> ReturnApproved : RMA issued
    ReturnRequested --> ReturnDenied : Outside policy

    ReturnApproved --> ReturnReceived : Warehouse receives
    ReturnReceived --> RefundInitiated : Inspection passed
    ReturnReceived --> ReturnDenied : Inspection failed

    RefundInitiated --> Refunded : Funds returned
    Refunded --> [*]

    ReturnDenied --> Delivered : Item shipped back to customer

    Disputed --> UnderReview : Fraud team investigates
    UnderReview --> Refunded : Dispute upheld
    UnderReview --> Delivered : Dispute denied

    Cancelled --> [*]
```
