# OAuth 2.0 Authentication Flow

This diagram shows the complete OAuth 2.0 authorization code flow with PKCE,
including token refresh, session management, and error handling paths.

```mermaid
flowchart TD
    A([User opens app]) --> B{Has valid session?}
    B -->|Yes| C[Load Dashboard]
    B -->|No| D[Redirect to Login]

    D --> E[/User enters email & password/]
    E --> F{Credentials valid?}
    F -->|No| G[Show error toast]
    G --> D

    F -->|Yes| H{MFA enabled?}
    H -->|No| I[Generate auth code]
    H -->|Yes| J[/Enter TOTP code/]
    J --> K{TOTP valid?}
    K -->|No| L[Show MFA error]
    L --> J
    K -->|Yes| I

    I --> M[Exchange code for tokens]
    M --> N[(Token Store)]
    N --> O[Set HTTP-only cookie]
    O --> P[Set refresh token]
    P --> C

    C --> Q{API request}
    Q --> R{Access token expired?}
    R -->|No| S[Forward request to API]
    R -->|Yes| T[Use refresh token]
    T --> U{Refresh valid?}
    U -->|Yes| V[Issue new access token]
    V --> N
    U -->|No| W[Clear session]
    W --> D

    S --> X{Response OK?}
    X -->|200| Y[Render data]
    X -->|401| W
    X -->|403| Z[Show forbidden page]
    X -->|5xx| AA[Show error page + retry]
```

## Flow Summary

1. **Entry** — Check for existing valid session
2. **Login** — Email/password with optional MFA (TOTP)
3. **Token exchange** — Auth code → access + refresh tokens
4. **Session** — HTTP-only cookies, automatic refresh
5. **Error paths** — 401 forces re-auth, 403 shows forbidden, 5xx retries
