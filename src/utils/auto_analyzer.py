"""Deep content analyzer — converts raw text into the optimal diagram type.

Extraction pipeline:
  1. Preprocess: normalize, split sentences/lines, detect structure
  2. Entity extraction: tech names, service patterns, generic components
  3. Relationship extraction: arrows, verbs, prepositions, proximity
  4. Hierarchy detection: headings, indentation, category language
  5. Process detection: numbered steps, sequential language, decisions
  6. Interaction detection: actor↔actor message passing
  7. State detection: state names + transition triggers
  8. Temporal detection: dates, milestones, phases
  9. Scoring: weighted signals per diagram type
  10. Syntax generation: convert extracted features to renderable syntax
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════════════════
# §1  CONSTANTS & PATTERN BANKS
# ═══════════════════════════════════════════════════════════════════════════════

# Technology names — aligned with KEYWORD_ICON_MAP in icon_registry.py
_TECH_NAMES: dict[str, str] = {
    "postgresql": "PostgreSQL",   "postgres": "PostgreSQL",
    "mysql": "MySQL",             "mariadb": "MariaDB",
    "mongodb": "MongoDB",         "mongo": "MongoDB",
    "dynamodb": "DynamoDB",       "cockroachdb": "CockroachDB",
    "sqlite": "SQLite",           "elasticsearch": "Elasticsearch",
    "redis": "Redis",             "memcached": "Memcached",
    "kafka": "Kafka",             "rabbitmq": "RabbitMQ",
    "nats": "NATS",               "mqtt": "MQTT",
    "docker": "Docker",           "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",          "podman": "Podman",
    "nginx": "Nginx",             "envoy": "Envoy",
    "istio": "Istio",             "linkerd": "Linkerd",
    "consul": "Consul",           "etcd": "etcd",
    "jenkins": "Jenkins",         "circleci": "CircleCI",
    "terraform": "Terraform",     "ansible": "Ansible",
    "prometheus": "Prometheus",    "grafana": "Grafana",
    "datadog": "Datadog",         "sentry": "Sentry",
    "newrelic": "New Relic",
    "aws": "AWS",                 "azure": "Azure",
    "gcp": "GCP",                 "google cloud": "Google Cloud",
    "cloudflare": "Cloudflare",   "vercel": "Vercel",
    "heroku": "Heroku",           "digitalocean": "DigitalOcean",
    "react": "React",             "nextjs": "Next.js",
    "next.js": "Next.js",         "vue": "Vue",
    "angular": "Angular",         "svelte": "Svelte",
    "nodejs": "Node.js",          "node.js": "Node.js",
    "python": "Python",           "golang": "Go",
    "java": "Java",               "rust": "Rust",
    ".net": ".NET",               "dotnet": ".NET",
    "graphql": "GraphQL",         "grpc": "gRPC",
    "oauth": "OAuth",             "vault": "Vault",
    "lambda": "Lambda",           "s3": "S3",
    "bigquery": "BigQuery",       "snowflake": "Snowflake",
    "spark": "Spark",             "airflow": "Airflow",
    "tensorflow": "TensorFlow",   "pytorch": "PyTorch",
    "openai": "OpenAI",           "stripe": "Stripe",
    "twilio": "Twilio",           "slack": "Slack",
    "jira": "Jira",               "github": "GitHub",
    "gitlab": "GitLab",           "sendgrid": "SendGrid",
    "haproxy": "HAProxy",         "traefik": "Traefik",
    "apache": "Apache",           "tomcat": "Tomcat",
    "celery": "Celery",           "sidekiq": "Sidekiq",
    "firebase": "Firebase",       "supabase": "Supabase",
}

_TECH_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_TECH_NAMES.keys(), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Service/component suffixes — "X <suffix>" → entity
_SERVICE_SUFFIXES = [
    "service", "server", "database", "cache", "queue", "gateway",
    "proxy", "balancer", "cluster", "registry", "dashboard",
    "pipeline", "engine", "bus", "broker", "store", "manager",
    "controller", "handler", "provider", "scheduler", "worker",
    "processor", "dispatcher", "listener", "adapter", "connector",
    "router", "layer", "pool", "node", "instance", "replica",
    "frontend", "backend", "api", "app", "application", "client",
    "network", "firewall", "cdn", "dns", "vpn",
]

_SERVICE_SUFFIX_RE = re.compile(
    r"(?:^|[\s,;])((?:[A-Z][\w.-]*[ \t]+)*(?:" +
    "|".join(re.escape(s) for s in _SERVICE_SUFFIXES) +
    r")(?:[ \t]+(?:system|module|component|platform|hub|stack|suite|tool))?)\b",
    re.IGNORECASE,
)

# Relationship verbs — connect entities
_REL_VERBS = re.compile(
    r"\b(connects?\s+to|talks?\s+to|sends?\s+(?:data\s+)?to|"
    r"calls?|queries|requests?|reads?\s+from|writes?\s+to|"
    r"routes?\s+to|forwards?\s+to|redirects?\s+to|"
    r"publishes?\s+(?:events?\s+)?to|subscribes?\s+to|"
    r"pushes?\s+to|pulls?\s+from|"
    r"triggers?|invokes?|notifies?|"
    r"depends?\s+on|relies?\s+on|"
    r"stores?\s+(?:data\s+)?in|persists?\s+(?:data\s+)?in|"
    r"caches?\s+in|logs?\s+to|"
    r"feeds?\s+into|pipes?\s+(?:data\s+)?to|"
    r"proxies?\s+to|load[- ]?balances?\s+(?:to|across)|"
    r"authenticates?\s+(?:against|via|through|with)|"
    r"consumes?\s+from|produces?\s+to|"
    r"serves?|exposes?|provides?|returns?)\b",
    re.IGNORECASE,
)

_ARROW_DELIM_RE = re.compile(r"\s*(?:-->|->|→|=>|——>|—>)\s*")

_PREP_CONN_RE = re.compile(
    r"\bfrom\s+([\w\s]+?)\s+to\s+([\w\s]+?)(?:\.|,|;|\band\b|$)",
    re.IGNORECASE,
)
_THROUGH_RE = re.compile(
    r"([\w\s]+?)\s+(?:through|via|using)\s+([\w\s]+?)(?:\.|,|;|\band\b|$)",
    re.IGNORECASE,
)

# Layer/group keywords for auto-grouping
_LAYER_KEYWORDS: dict[str, list[str]] = {
    "Client Layer": [
        "browser", "frontend", "client", "web app", "mobile app",
        "desktop", "ui", "user interface", "spa", "pwa",
    ],
    "Edge & Networking": [
        "cdn", "load balancer", "dns", "reverse proxy", "waf",
        "firewall", "vpn", "edge", "cloudflare", "nginx", "haproxy",
        "traefik", "ingress",
    ],
    "API & Gateway": [
        "api gateway", "api server", "gateway", "graphql",
        "grpc", "rest api", "api",
    ],
    "Auth & Security": [
        "auth", "authentication", "authorization", "oauth", "sso",
        "iam", "vault", "secret", "certificate", "jwt", "token",
        "encrypt", "security",
    ],
    "Core Services": [
        "service", "handler", "processor", "controller",
        "manager", "scheduler", "worker", "engine",
    ],
    "Data & Storage": [
        "database", "db", "sql", "postgres", "mysql", "mongo",
        "dynamo", "cockroach", "sqlite", "storage", "s3", "blob",
        "bucket", "data warehouse", "data lake", "bigquery", "snowflake",
    ],
    "Cache & Memory": [
        "cache", "redis", "memcached", "session store",
    ],
    "Messaging & Events": [
        "kafka", "rabbitmq", "nats", "mqtt", "queue", "message bus",
        "event bus", "pub/sub", "stream", "broker",
    ],
    "Compute & Runtime": [
        "kubernetes", "k8s", "docker", "container", "lambda",
        "serverless", "function", "ec2", "vm", "instance",
        "server", "compute",
    ],
    "CI/CD & DevOps": [
        "ci/cd", "pipeline", "jenkins", "github actions", "gitlab",
        "circleci", "deploy", "build", "test", "release",
        "terraform", "ansible", "helm", "argocd",
    ],
    "Monitoring & Observability": [
        "monitor", "prometheus", "grafana", "datadog", "logging",
        "metric", "alert", "dashboard", "observability", "tracing",
        "sentry", "newrelic", "elastic", "kibana",
    ],
    "Notification & Communication": [
        "notification", "email", "sms", "push", "slack",
        "twilio", "sendgrid", "webhook", "alert",
    ],
    "AI & ML": [
        "ml", "machine learning", "ai", "model", "training",
        "tensorflow", "pytorch", "openai", "inference",
    ],
    "Analytics & BI": [
        "analytics", "report", "dashboard", "chart", "bi",
        "power bi", "tableau", "metabase",
    ],
}

# Flowchart language
_SEQUENTIAL_RE = re.compile(
    r"\b(first|then|next|after\s+that|finally|subsequently|"
    r"followed\s+by|once|before|step\s*\d+|stage\s*\d+)\b",
    re.IGNORECASE,
)
_DECISION_RE = re.compile(
    r"\b(if|when|check|decide|validate|verify|whether|condition|"
    r"branch|else|otherwise|approve|reject|accept|deny|pass|fail|"
    r"success|error|true|false|yes|no)\b",
    re.IGNORECASE,
)
_NUMBERED_STEP_RE = re.compile(r"^\s*(\d+)\s*[.\)]\s+(.+)", re.MULTILINE)

# Sequence diagram language
_ACTOR_VERB_RE = re.compile(
    r"\b(user|client|browser|server|api|service|database|db|system|"
    r"admin|customer|actor|participant|sender|receiver|producer|consumer|"
    r"caller|callee|requester|responder|publisher|subscriber)\b",
    re.IGNORECASE,
)
_MSG_PATTERN_RE = re.compile(
    r"([\w\s]+?)\s+(?:sends?|returns?|responds?\s+with|replies?\s+with|"
    r"requests?|asks?|tells?|notifies?|calls?|invokes?)\s+"
    r"(?:a\s+|the\s+|an?\s+)?([\w\s]+?)\s+"
    r"(?:to|from)\s+([\w\s]+?)(?:\.|,|;|$)",
    re.IGNORECASE,
)

# State diagram language — tiered to avoid false positives on common words
_STRONG_STATE_WORDS = frozenset({
    "pending", "approved", "rejected", "processing", "submitted",
    "draft", "published", "archived", "suspended", "terminated",
    "initialized", "paused", "cancelled", "in_progress",
})
_WEAK_STATE_WORDS = frozenset({
    "open", "closed", "new", "error", "done", "active", "inactive",
    "idle", "running", "stopped", "started", "completed", "failed",
    "waiting", "locked", "unlocked", "enabled", "disabled",
    "resumed", "created", "updated", "deleted", "verified",
    "unverified", "expired", "timeout",
})
_ALL_STATE_WORDS = _STRONG_STATE_WORDS | _WEAK_STATE_WORDS
_STATE_WORDS = re.compile(
    r"\b(" + "|".join(
        re.escape(w).replace(r"\_", r"[\s_]")
        for w in sorted(_ALL_STATE_WORDS, key=len, reverse=True)
    ) + r")\b",
    re.IGNORECASE,
)
_STATE_CONTEXT_RE = re.compile(
    r"\b(state|status|transition|lifecycle|state\s+machine|"
    r"workflow\s+state|state\s+diagram|finite\s+state|fsm)\b",
    re.IGNORECASE,
)
_TRANSITION_RE = re.compile(
    r"([\w\s]+?)\s*(?:->|→|=>|transitions?\s+to|moves?\s+to|"
    r"changes?\s+to|becomes?|goes?\s+to)\s*([\w\s]+?)(?:\.|,|;|\band\b|$)",
    re.IGNORECASE,
)

# Timeline / date language
_DATE_RE = re.compile(
    r"\b(\d{4}[-/]\d{1,2}(?:[-/]\d{1,2})?|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{4}|"
    r"Q[1-4]\s*['\u2019]?\d{2,4}|"
    r"Phase\s+\d+|Sprint\s+\d+|Week\s+\d+|Month\s+\d+|"
    r"Year\s+\d+|Day\s+\d+|"
    r"v\d+\.\d+)\b",
    re.IGNORECASE,
)
_MILESTONE_RE = re.compile(
    r"\b(launch|release|milestone|deadline|kickoff|go[- ]live|"
    r"beta|alpha|mvp|ga|rc\d*|eol)\b",
    re.IGNORECASE,
)

# ER diagram language
_ER_ENTITY_RE = re.compile(
    r"\b(table|entity|model|schema|record|document|collection|"
    r"object|resource|type)\b",
    re.IGNORECASE,
)
_ER_ATTR_RE = re.compile(
    r"\b(field|column|attribute|property|key|id|name|type|"
    r"foreign\s+key|primary\s+key|index|unique|nullable|"
    r"varchar|integer|boolean|text|timestamp|uuid|serial|"
    r"string|number|float|decimal|date|datetime|enum|json|"
    r"array|blob|binary)\b",
    re.IGNORECASE,
)
_ER_REL_RE = re.compile(
    r"\b(has\s+many|has\s+one|belongs?\s+to|many[- ]to[- ]many|"
    r"one[- ]to[- ]many|one[- ]to[- ]one|references?|"
    r"foreign\s+key|FK|PK|joins?\s+to|associated\s+with)\b",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# §2  DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Entity:
    name: str
    canonical: str
    source: str  # "tech", "pattern", "arrow", "noun_phrase"
    original_span: str = ""

@dataclass
class Relationship:
    src: str
    dst: str
    verb: str = ""

@dataclass
class HierarchyNode:
    text: str
    children: list["HierarchyNode"] = field(default_factory=list)

@dataclass
class Step:
    index: int
    text: str
    is_decision: bool = False

@dataclass
class Interaction:
    actor_from: str
    message: str
    actor_to: str

@dataclass
class StateTransition:
    from_state: str
    trigger: str
    to_state: str

@dataclass
class TimelineEvent:
    date: str
    description: str


# ═══════════════════════════════════════════════════════════════════════════════
# §3  TEXT PREPROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _split_sentences(text: str) -> list[str]:
    """Split into sentences, keeping bullet/list items as atomic units."""
    sentences: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if re.match(r"^[-*+•]\s+", line) or re.match(r"^\d+[.)]\s+", line):
            sentences.append(re.sub(r"^[-*+•\d.)\s]+", "", line).strip())
            continue
        if line.startswith("#"):
            sentences.append(line.lstrip("#").strip())
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences


def _detect_structure(lines: list[str]) -> dict:
    """Detect document structure: headings, bullets, numbered, tables, paragraphs."""
    counts = {
        "headings": 0, "bullets": 0, "numbered": 0,
        "tables": 0, "arrows": 0, "paragraphs": 0,
        "indented_blocks": 0,
    }
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            counts["headings"] += 1
        elif re.match(r"^[-*+•]\s+", stripped):
            counts["bullets"] += 1
        elif re.match(r"^\d+[.)]\s+", stripped):
            counts["numbered"] += 1
        elif stripped.startswith("|") and "|" in stripped[1:]:
            counts["tables"] += 1
        elif "->" in stripped or "→" in stripped or "=>" in stripped:
            counts["arrows"] += 1
        elif len(line) > len(line.lstrip()) and len(line.lstrip()) > 0:
            counts["indented_blocks"] += 1
        else:
            counts["paragraphs"] += 1
    return counts


# ═══════════════════════════════════════════════════════════════════════════════
# §4  ENTITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_arrow_chains(text: str) -> tuple[list[str], list[tuple[str, str]], int]:
    """Parse arrow-notation lines (A -> B -> C) into entities and edges.

    Returns (entities, edges, message_line_count).
    message_line_count = how many arrow lines have ": message" labels
    (a strong signal for sequence diagrams over architecture).
    """
    arrow_entities: list[str] = []
    arrow_edges: list[tuple[str, str]] = []
    seen: set[str] = set()
    msg_lines = 0

    for line in text.split("\n"):
        stripped = line.strip()
        if not _ARROW_DELIM_RE.search(stripped):
            continue
        if stripped.startswith("#"):
            continue

        parts = _ARROW_DELIM_RE.split(stripped)
        parts = [p.strip().rstrip(".:;,") for p in parts if p.strip()]

        # Detect and strip colon-delimited message labels
        # "Browser: Opens login page" → entity="Browser", has_msg=True
        clean_parts: list[str] = []
        has_msg = False
        for p in parts:
            if ":" in p:
                entity_part = p.split(":", 1)[0].strip()
                has_msg = True
                clean_parts.append(entity_part if entity_part else p)
            else:
                clean_parts.append(p)
        if has_msg:
            msg_lines += 1

        for p in clean_parts:
            if p and len(p) > 1 and p.lower() not in seen:
                seen.add(p.lower())
                arrow_entities.append(p)
        for i in range(len(clean_parts) - 1):
            if clean_parts[i] and clean_parts[i + 1]:
                arrow_edges.append((clean_parts[i], clean_parts[i + 1]))

    return arrow_entities, arrow_edges, msg_lines


_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "it", "its", "this", "that",
    "these", "those", "we", "our", "they", "their", "he", "she", "which",
    "where", "when", "then", "also", "both", "each", "every", "all", "some",
    "most", "very", "such", "about", "into", "not", "no", "if", "so",
})


def _is_clean_entity(name: str) -> bool:
    """Filter out sentence fragments, stopwords, and garbage entities."""
    if len(name) < 2 or len(name) > 50:
        return False
    words = name.lower().split()
    if not words:
        return False
    if words[0] in _STOPWORDS:
        return False
    if len(words) > 5:
        return False
    # Reject if it looks like a sentence (contains common verb forms)
    sentence_verbs = {
        "consists", "connects", "handles", "processes", "publishes",
        "deploys", "manages", "stores", "runs", "uses", "powers",
        "backed", "feeds", "orchestrated", "powered",
        "integrates", "communicates", "sends", "receives", "triggers",
        "monitors", "routes", "serves", "exposes", "provides",
        "produces", "consumes", "invokes", "forwards", "proxies",
        "logs", "caches", "talks", "calls", "queries", "writes",
        "reads", "schedules", "dispatches", "listens",
    }
    if any(w in sentence_verbs for w in words):
        return False
    return True


def _strip_arrow_lines(text: str) -> str:
    """Return text with arrow-notation lines removed."""
    return "\n".join(
        line for line in text.split("\n")
        if not _ARROW_DELIM_RE.search(line)
    )


def _clean_bullet_item(item: str) -> str:
    """Strip trailing descriptors from bullet items: 'Foo with bar' → 'Foo'."""
    cut_words = re.compile(
        r"\s+(?:with|for|using|via|powered\s+by|backed\s+by|based\s+on|"
        r"which|that|where|to|from|in|on|at|stores|persists|sessions|"
        r"integrates|communicates|connects|sends|receives|manages|"
        r"handles|processes|publishes|monitors|routes|triggers|"
        r"and\s+\w+\s+\w+)\b.*$",
        re.IGNORECASE,
    )
    cleaned = cut_words.sub("", item).strip().rstrip(".:;,")
    return cleaned if len(cleaned) > 1 else item.strip().rstrip(".:;,")


def _extract_entities(text: str, sentences: list[str]) -> list[Entity]:
    """Multi-pass entity extraction: tech names, service patterns, arrow endpoints."""
    entities: list[Entity] = []
    seen_lower: set[str] = set()
    safe_text = _strip_arrow_lines(text)

    def _add(name: str, canonical: str, source: str, span: str = "") -> None:
        key = canonical.lower()
        if key not in seen_lower and _is_clean_entity(canonical):
            seen_lower.add(key)
            entities.append(Entity(name=name, canonical=canonical, source=source, original_span=span))

    # Pass 1: Known technology names (full text — tech names are unambiguous)
    for m in _TECH_PATTERN.finditer(text):
        raw = m.group(0).lower()
        canon = _TECH_NAMES.get(raw, m.group(0))
        _add(raw, canon, "tech", m.group(0))

    # Pass 2: Service/component patterns on safe text (per-line to avoid cross-line matches)
    for line in safe_text.split("\n"):
        for m in _SERVICE_SUFFIX_RE.finditer(line):
            raw = m.group(1).strip()
            if len(raw) <= 2 or raw.lower() in _STOPWORDS:
                continue
            words = raw.split()
            clean_words: list[str] = []
            for w in words:
                if w.lower() in _STOPWORDS:
                    clean_words = []
                else:
                    clean_words.append(w)
            cleaned = " ".join(clean_words).strip()
            if cleaned and len(cleaned) > 1 and len(cleaned.split()) <= 4:
                canon = _titlecase(cleaned)
                _add(cleaned.lower(), canon, "pattern", cleaned)

    # Pass 3: Arrow chain endpoints (extracted from arrow lines)
    arrow_entities, _, _ = _extract_arrow_chains(text)
    for ae in arrow_entities:
        _add(ae.lower(), _titlecase(ae), "arrow", ae)

    # Pass 4: Bullet list items (commonly service names in docs)
    for line in text.split("\n"):
        stripped = line.strip()
        if _ARROW_DELIM_RE.search(stripped):
            continue
        m = re.match(r"^[-*+•]\s+(.+)", stripped)
        if m:
            item = _clean_bullet_item(m.group(1))
            words = item.split()
            if 1 <= len(words) <= 5 and _is_clean_entity(item):
                if not any(item.lower() == s for s in seen_lower):
                    _add(item.lower(), _titlecase(item), "bullet", item)

    # Pass 5: Capitalized multi-word phrases on safe text (no arrow lines)
    # Use [ \t]+ instead of \s+ to avoid cross-line matching
    cap_re = re.compile(r"\b([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,3})\b")
    for m in cap_re.finditer(safe_text):
        phrase = m.group(1).strip()
        if _is_clean_entity(phrase):
            _add(phrase.lower(), phrase, "noun_phrase", phrase)

    # Pass 6: Deduplicate — remove entity X if a longer entity Y starts with X
    to_remove: set[str] = set()
    for i, e in enumerate(entities):
        name_l = e.canonical.lower()
        for j, other in enumerate(entities):
            if i == j:
                continue
            other_l = other.canonical.lower()
            if len(name_l) < len(other_l):
                if other_l.startswith(name_l + " ") or other_l.endswith(" " + name_l):
                    to_remove.add(e.canonical)
                    break

    if to_remove:
        entities = [e for e in entities if e.canonical not in to_remove]

    return entities


def _titlecase(s: str) -> str:
    """Smart title case preserving known acronyms."""
    acronyms = {"api", "cdn", "dns", "vpn", "ssl", "tls", "http", "https",
                "sql", "db", "ci", "cd", "ui", "ux", "jwt", "sso", "iam",
                "aws", "gcp", "s3", "ec2", "rds", "sqs", "sns", "ecs", "eks",
                "grpc", "mqtt", "amqp", "smtp", "imap", "ldap"}
    words = s.split()
    result = []
    for w in words:
        if w.lower() in acronyms:
            result.append(w.upper())
        else:
            result.append(w.capitalize())
    return " ".join(result)


# ═══════════════════════════════════════════════════════════════════════════════
# §5  RELATIONSHIP EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_relationships(
    text: str,
    sentences: list[str],
    entities: list[Entity],
) -> list[Relationship]:
    """Extract connections between entities from arrows, verbs, and prepositions."""
    rels: list[Relationship] = []
    seen: set[tuple[str, str]] = set()
    entity_lower_map = {e.canonical.lower(): e.canonical for e in entities}

    def _resolve(raw: str) -> str | None:
        """Resolve raw text to a known entity — exact, word-overlap, substring."""
        raw_l = raw.strip().lower()
        if raw_l in entity_lower_map:
            return entity_lower_map[raw_l]
        # Word-overlap: "load balancer" matches "Nginx Load Balancer"
        raw_words = set(raw_l.split())
        if len(raw_words) >= 2:
            best, best_n = None, 0
            for canon_l, canon in entity_lower_map.items():
                canon_words = set(canon_l.split())
                overlap = len(raw_words & canon_words)
                if overlap == len(raw_words) and overlap > best_n:
                    best_n = overlap
                    best = canon
            if best:
                return best
        # Substring containment (both directions)
        for canon_l, canon in entity_lower_map.items():
            if len(raw_l) > 3 and (raw_l in canon_l or canon_l in raw_l):
                return canon
        return None

    def _add_rel(src: str, dst: str, verb: str = "") -> None:
        key = (src, dst)
        if key not in seen and src != dst:
            seen.add(key)
            rels.append(Relationship(src=src, dst=dst, verb=verb))

    # Pass 1: Arrow chains (A -> B -> C parsed as edges)
    _, arrow_edges, _ = _extract_arrow_chains(text)
    for src_raw, dst_raw in arrow_edges:
        src = _resolve(src_raw)
        dst = _resolve(dst_raw)
        if src and dst:
            _add_rel(src, dst, "->")

    # Pass 2: Verb-based relationships in each sentence (with fuzzy matching)
    for sent in sentences:
        sent_lower = sent.lower()
        found_entities: list[tuple[int, str]] = []
        matched_spans: set[tuple[int, int]] = set()

        # Exact canonical match first
        for e in entities:
            canon_l = e.canonical.lower()
            idx = sent_lower.find(canon_l)
            if idx >= 0:
                span = (idx, idx + len(canon_l))
                overlap = any(
                    s < idx + len(canon_l) and idx < e2
                    for s, e2 in matched_spans
                )
                if not overlap:
                    found_entities.append((idx, e.canonical))
                    matched_spans.add(span)

        # Core-word fuzzy: "load balancer" → "Nginx Load Balancer"
        for e in entities:
            if e.canonical in {f[1] for f in found_entities}:
                continue
            words = e.canonical.lower().split()
            if len(words) < 2:
                continue
            core = " ".join(words[-2:])
            idx = sent_lower.find(core)
            if idx >= 0 and not any(s < idx + len(core) and idx < e2 for s, e2 in matched_spans):
                found_entities.append((idx, e.canonical))
                matched_spans.add((idx, idx + len(core)))

        found_entities.sort(key=lambda x: x[0])
        if len(found_entities) < 2:
            continue

        for verb_m in _REL_VERBS.finditer(sent):
            verb_pos = verb_m.start()
            before = [(pos, name) for pos, name in found_entities if pos < verb_pos]
            after = [(pos, name) for pos, name in found_entities if pos > verb_pos]

            if before and after:
                _add_rel(before[-1][1], after[0][1], verb_m.group(0))

        # Fallback: verb-root proximity — catches "routes traffic to"
        if not any(_REL_VERBS.finditer(sent)):
            verb_roots = re.compile(
                r"\b(connect|talk|send|call|route|forward|redirect|publish|"
                r"subscribe|push|pull|trigger|invoke|notif|store|persist|"
                r"cache|log|feed|pipe|proxy|balanc|authenticat|consum|"
                r"produc|serv|expos|provid|return|depend|rel)\w*\b",
                re.IGNORECASE,
            )
            if verb_roots.search(sent):
                for k in range(len(found_entities) - 1):
                    e1_pos = found_entities[k][0]
                    e2_pos = found_entities[k + 1][0]
                    between = sent[e1_pos:e2_pos].lower()
                    if verb_roots.search(between):
                        _add_rel(found_entities[k][1], found_entities[k + 1][1], "connects")
            elif len(found_entities) == 2:
                if any(w in sent_lower for w in ("through", "via", "using", "with")):
                    _add_rel(found_entities[0][1], found_entities[1][1], "uses")

    # Pass 3: Preposition connections — "from A to B"
    for m in _PREP_CONN_RE.finditer(text):
        src = _resolve(m.group(1))
        dst = _resolve(m.group(2))
        if src and dst:
            _add_rel(src, dst, "from..to")

    # Pass 4: "through/via" connections — "A through B"
    for m in _THROUGH_RE.finditer(text):
        src = _resolve(m.group(1))
        mid = _resolve(m.group(2))
        if src and mid:
            _add_rel(src, mid, "through")

    return rels


# ═══════════════════════════════════════════════════════════════════════════════
# §6  HIERARCHY EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_hierarchy(lines: list[str]) -> HierarchyNode | None:
    """Build a tree from headings + bullets / indentation."""
    root: HierarchyNode | None = None
    stack: list[tuple[int, HierarchyNode]] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped.lstrip("#").strip()
            if not text:
                continue

            node = HierarchyNode(text=text)
            if root is None:
                root = node
                stack = [(level, node)]
            else:
                while stack and stack[-1][0] >= level:
                    stack.pop()
                if stack:
                    stack[-1][1].children.append(node)
                else:
                    root.children.append(node)
                stack.append((level, node))

        elif re.match(r"^[-*+•]\s+", stripped):
            text = re.sub(r"^[-*+•]\s+", "", stripped).strip()
            indent = len(line) - len(line.lstrip())
            depth = indent // 2 + 100  # offset to avoid collision with heading levels

            node = HierarchyNode(text=text)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if stack:
                stack[-1][1].children.append(node)
            elif root:
                root.children.append(node)
            else:
                root = node
            stack.append((depth, node))

    return root


def _count_tree_nodes(node: HierarchyNode) -> int:
    return 1 + sum(_count_tree_nodes(c) for c in node.children)


def _tree_depth(node: HierarchyNode) -> int:
    if not node.children:
        return 1
    return 1 + max(_tree_depth(c) for c in node.children)


# ═══════════════════════════════════════════════════════════════════════════════
# §7  PROCESS / FLOWCHART EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_steps(text: str, lines: list[str], sentences: list[str]) -> list[Step]:
    """Extract process steps from numbered lists and sequential language."""
    steps: list[Step] = []

    # Numbered steps
    for m in _NUMBERED_STEP_RE.finditer(text):
        idx = int(m.group(1))
        step_text = m.group(2).strip()
        is_dec = bool(_DECISION_RE.search(step_text))
        steps.append(Step(index=idx, text=step_text, is_decision=is_dec))

    if steps:
        steps.sort(key=lambda s: s.index)
        return steps

    # Fallback: sentences with sequential language
    seq_sentences = [s for s in sentences if _SEQUENTIAL_RE.search(s)]
    if len(seq_sentences) >= 3:
        for i, s in enumerate(seq_sentences):
            is_dec = bool(_DECISION_RE.search(s))
            steps.append(Step(index=i + 1, text=s, is_decision=is_dec))
        return steps

    # Fallback: bullet lists with enough items that have process language
    bullet_items = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*+•]\s+", stripped):
            item = re.sub(r"^[-*+•]\s+", "", stripped).strip()
            if item:
                bullet_items.append(item)

    process_keywords = re.compile(
        r"\b(start|begin|end|finish|complete|send|receive|process|"
        r"create|update|delete|check|validate|verify|submit|approve|"
        r"reject|return|redirect|login|logout|sign|register|upload|"
        r"download|generate|compute|calculate|transform|filter|sort)\b",
        re.IGNORECASE,
    )
    if len(bullet_items) >= 4:
        process_count = sum(1 for item in bullet_items if process_keywords.search(item))
        if process_count >= len(bullet_items) * 0.4:
            for i, item in enumerate(bullet_items):
                is_dec = bool(_DECISION_RE.search(item))
                steps.append(Step(index=i + 1, text=item, is_decision=is_dec))

    return steps


# ═══════════════════════════════════════════════════════════════════════════════
# §8  SEQUENCE / INTERACTION EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_interactions(text: str, sentences: list[str]) -> list[Interaction]:
    """Extract actor↔actor message interactions for sequence diagrams."""
    interactions: list[Interaction] = []

    # Pattern: "Actor sends/returns X to/from Actor"
    for m in _MSG_PATTERN_RE.finditer(text):
        interactions.append(Interaction(
            actor_from=_titlecase(m.group(1).strip()),
            message=m.group(2).strip(),
            actor_to=_titlecase(m.group(3).strip()),
        ))

    # Pattern: "A -> B: message" (per-line to avoid cross-line pollution)
    arrow_msg_re = re.compile(
        r"^([\w ]+?)\s*(?:->|→|=>)\s*([\w ]+?)\s*:\s*(.+)$",
        re.MULTILINE,
    )
    for m in arrow_msg_re.finditer(text):
        interactions.append(Interaction(
            actor_from=_titlecase(m.group(1).strip()),
            message=m.group(3).strip(),
            actor_to=_titlecase(m.group(2).strip()),
        ))

    # Pattern: sentences with two actors and a verb (skip if arrows already covered)
    covered = {(i.actor_from.lower(), i.actor_to.lower()) for i in interactions}
    for sent in sentences:
        if "->" in sent or "→" in sent or "=>" in sent:
            continue
        actors_found = []
        for m in _ACTOR_VERB_RE.finditer(sent):
            actors_found.append((m.start(), _titlecase(m.group(0))))

        if len(actors_found) >= 2:
            pair = (actors_found[0][1].lower(), actors_found[1][1].lower())
            if pair in covered:
                continue
            verb_m = re.search(
                r"\b(sends?|returns?|responds?|requests?|calls?|"
                r"notifies?|invokes?|queries|forwards?|asks?)\b",
                sent, re.IGNORECASE,
            )
            if verb_m:
                msg = sent[actors_found[0][0] + len(actors_found[0][1]):verb_m.start()].strip()
                if not msg:
                    msg = verb_m.group(0)
                interactions.append(Interaction(
                    actor_from=actors_found[0][1],
                    message=msg or verb_m.group(0),
                    actor_to=actors_found[1][1],
                ))

    return interactions


# ═══════════════════════════════════════════════════════════════════════════════
# §9  STATE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

_TRANS_DEST_RE = re.compile(
    r"(?:transitions?\s+to|moves?\s+to|changes?\s+to|"
    r"becomes?|goes?\s+to)\s+"
    r"([A-Z][\w]+(?: [A-Z][\w]+)*)",
)
_STATE_LABEL_RE = re.compile(
    r"(?:the|in(?:\s+the)?)\s+([\w]+(?: [\w]+){0,2})\s+(?:state|status)\b",
    re.IGNORECASE,
)
_FROM_TO_STATE_RE = re.compile(
    r"(?:goes?\s+from|from)\s+([\w]+(?: [\w]+){0,2})\s+to\s+([\w]+(?: [\w]+){0,2})",
    re.IGNORECASE,
)


def _extract_states(text: str, sentences: list[str]) -> tuple[list[str], list[StateTransition]]:
    """Multi-phase state and transition extraction.

    Phase 1: Static word list (tiered strong/weak)
    Phase 2: Transition-verb destinations ("transitions to Shipped" → Shipped)
    Phase 3: Explicit label patterns ("the Submitted state" → Submitted)
    Phase 4: Build transitions from consecutive state mentions per sentence
    Phase 5: "from X to Y" patterns
    """
    seen: set[str] = set()
    states: list[str] = []

    def _add_state(name: str) -> None:
        tc = _titlecase(name)
        if tc.lower() not in seen and len(tc) > 1 and len(tc.split()) <= 4:
            seen.add(tc.lower())
            states.append(tc)

    has_context = bool(_STATE_CONTEXT_RE.search(text))

    # Phase 1: Static word lists
    strong_found: set[str] = set()
    weak_found: set[str] = set()
    for m in _STATE_WORDS.finditer(text):
        word = m.group(0).lower().replace("_", " ").strip()
        if word in _STRONG_STATE_WORDS:
            strong_found.add(word)
        else:
            weak_found.add(word)
    use_weak = len(strong_found) >= 2 or has_context
    for w in strong_found | (weak_found if use_weak else set()):
        _add_state(w)

    # Phase 2a: Transition-verb destinations
    for m in _TRANS_DEST_RE.finditer(text):
        _add_state(m.group(1).strip())

    # Phase 2b: Lines with transition verbs — capture "to [Capitalized]"
    _trans_line_re = re.compile(
        r"\b(?:transition|mov|chang|becom|go(?:es|ing)?)\w*\b", re.IGNORECASE,
    )
    _to_cap_re = re.compile(r"\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)")
    for line in text.split("\n"):
        if _trans_line_re.search(line):
            for m in _to_cap_re.finditer(line):
                _add_state(m.group(1).strip())

    # Phase 3: "the X state" / "in the X state"
    for m in _STATE_LABEL_RE.finditer(text):
        _add_state(m.group(1).strip())

    # Phase 4: Sentence-level consecutive state mentions → transitions
    state_lookup = {s.lower(): s for s in states}
    transitions: list[StateTransition] = []
    seen_trans: set[tuple[str, str]] = set()

    for sent in sentences:
        sent_lower = sent.lower()
        hits: list[tuple[int, str]] = []
        for sl, sc in state_lookup.items():
            idx = sent_lower.find(sl)
            if idx >= 0:
                hits.append((idx, sc))
        hits.sort(key=lambda x: x[0])
        for i in range(len(hits) - 1):
            src, dst = hits[i][1], hits[i + 1][1]
            if src != dst and (src, dst) not in seen_trans:
                seen_trans.add((src, dst))
                transitions.append(StateTransition(from_state=src, trigger="", to_state=dst))

    # Phase 4b: State appearance chain — consecutive distinct states = transitions
    all_positions: list[tuple[int, str]] = []
    text_lower = text.lower()
    for sl, sc in state_lookup.items():
        idx = text_lower.find(sl)
        while idx >= 0:
            all_positions.append((idx, sc))
            idx = text_lower.find(sl, idx + len(sl))
    all_positions.sort(key=lambda x: x[0])
    prev_state = None
    for _, st in all_positions:
        if st != prev_state:
            if prev_state and (prev_state, st) not in seen_trans:
                seen_trans.add((prev_state, st))
                transitions.append(StateTransition(from_state=prev_state, trigger="", to_state=st))
            prev_state = st

    # Phase 5: "from X to Y" explicit pairs
    for m in _FROM_TO_STATE_RE.finditer(text):
        src_raw = _titlecase(m.group(1).strip())
        dst_raw = _titlecase(m.group(2).strip())
        src = state_lookup.get(src_raw.lower(), src_raw if src_raw.lower() in seen else None)
        dst = state_lookup.get(dst_raw.lower(), dst_raw if dst_raw.lower() in seen else None)
        if src and dst and src != dst and (src, dst) not in seen_trans:
            seen_trans.add((src, dst))
            transitions.append(StateTransition(from_state=src, trigger="", to_state=dst))

    return states, transitions


# ═══════════════════════════════════════════════════════════════════════════════
# §10  TIMELINE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_timeline(text: str, lines: list[str]) -> list[TimelineEvent]:
    """Extract date/milestone events for timeline diagrams."""
    events: list[TimelineEvent] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        date_m = _DATE_RE.search(stripped)
        if date_m:
            date_str = date_m.group(0)
            rest = stripped
            rest = re.sub(r"^[-*+•\d.)\s]+", "", rest).strip()
            rest = rest.replace(date_str, "").strip(" :–-—,")
            if rest and len(rest) > 2:
                events.append(TimelineEvent(date=date_str, description=rest))

    return events


# ═══════════════════════════════════════════════════════════════════════════════
# §11  ER EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_er_features(text: str, lines: list[str]) -> dict:
    """Extract entity-relationship features from text."""
    entity_count = len(_ER_ENTITY_RE.findall(text))
    attr_count = len(_ER_ATTR_RE.findall(text))
    rel_count = len(_ER_REL_RE.findall(text))

    # Detect markdown tables that look like entity definitions
    table_count = 0
    table_entities: list[dict] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            header = stripped
            if i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
                rows: list[str] = []
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    rows.append(lines[j].strip())
                    j += 1
                if rows:
                    table_count += 1
                    heading = ""
                    for k in range(i - 1, max(-1, i - 4), -1):
                        hl = lines[k].strip()
                        if hl.startswith("#"):
                            heading = hl.lstrip("#").strip()
                            break
                        if hl:
                            break
                    table_entities.append({"heading": heading, "header": header, "rows": rows})
                i = j
                continue
        i += 1

    return {
        "entity_count": entity_count,
        "attr_count": attr_count,
        "rel_count": rel_count,
        "table_count": table_count,
        "table_entities": table_entities,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# §12  SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def _score_types(
    entities: list[Entity],
    relationships: list[Relationship],
    hierarchy: HierarchyNode | None,
    steps: list[Step],
    interactions: list[Interaction],
    states: list[str],
    transitions: list[StateTransition],
    timeline_events: list[TimelineEvent],
    er_features: dict,
    structure: dict,
    arrow_msg_lines: int = 0,
) -> dict[str, float]:
    """Score each diagram type based on extracted features."""
    scores: dict[str, float] = {
        "architecture": 0.0,
        "mindmap": 0.0,
        "flowchart": 0.0,
        "sequenceDiagram": 0.0,
        "stateDiagram-v2": 0.0,
        "timeline": 0.0,
        "erDiagram": 0.0,
    }
    total_arrows = structure.get("arrows", 0)

    # ── Architecture scoring ──
    tech_entities = [e for e in entities if e.source == "tech"]
    pattern_entities = [e for e in entities if e.source == "pattern"]
    scores["architecture"] += len(tech_entities) * 2.0
    scores["architecture"] += len(pattern_entities) * 2.0
    scores["architecture"] += len(entities) * 0.5
    scores["architecture"] += len(relationships) * 2.5
    scores["architecture"] += total_arrows * 3.0
    if len(entities) >= 3 and len(relationships) >= 2:
        scores["architecture"] += 10.0
    # Penalize when text is clearly hierarchical — mindmap is a better fit
    if hierarchy:
        depth = _tree_depth(hierarchy)
        if depth >= 4 and structure.get("headings", 0) >= 3:
            scores["architecture"] *= 0.6
    # Dampen architecture when arrows are labeled (sequence pattern, not arch)
    if arrow_msg_lines >= 3 and total_arrows > 0:
        msg_ratio = arrow_msg_lines / max(total_arrows, 1)
        if msg_ratio > 0.5:
            scores["architecture"] *= 0.3

    # ── Mindmap scoring ──
    if hierarchy:
        node_count = _count_tree_nodes(hierarchy)
        depth = _tree_depth(hierarchy)
        scores["mindmap"] += node_count * 1.5
        scores["mindmap"] += depth * 2.5
        if node_count >= 5:
            scores["mindmap"] += 8.0
        if len(hierarchy.children) >= 3:
            scores["mindmap"] += 5.0
    scores["mindmap"] += structure.get("headings", 0) * 2.5
    scores["mindmap"] += structure.get("bullets", 0) * 0.8

    # ── Flowchart scoring ──
    scores["flowchart"] += len(steps) * 3.0
    decision_count = sum(1 for s in steps if s.is_decision)
    scores["flowchart"] += decision_count * 4.0
    scores["flowchart"] += structure.get("numbered", 0) * 2.0
    if len(steps) >= 4:
        scores["flowchart"] += 10.0

    # ── Sequence diagram scoring ──
    scores["sequenceDiagram"] += len(interactions) * 4.0
    if len(interactions) >= 3:
        scores["sequenceDiagram"] += 10.0
    unique_actors = {i.actor_from for i in interactions} | {i.actor_to for i in interactions}
    scores["sequenceDiagram"] += len(unique_actors) * 2.0
    # Arrow-with-message lines are a strong sequence signal
    scores["sequenceDiagram"] += arrow_msg_lines * 5.0

    # ── State diagram scoring ──
    scores["stateDiagram-v2"] += len(states) * 2.5
    scores["stateDiagram-v2"] += len(transitions) * 4.0
    if len(states) >= 3 and len(transitions) >= 2:
        scores["stateDiagram-v2"] += 10.0

    # ── Timeline scoring ──
    scores["timeline"] += len(timeline_events) * 4.0
    if len(timeline_events) >= 3:
        scores["timeline"] += 10.0

    # ── ER diagram scoring ──
    scores["erDiagram"] += er_features["entity_count"] * 1.5
    scores["erDiagram"] += er_features["attr_count"] * 1.0
    scores["erDiagram"] += er_features["rel_count"] * 3.0
    scores["erDiagram"] += er_features["table_count"] * 5.0
    if er_features["table_count"] >= 2 and er_features["rel_count"] >= 1:
        scores["erDiagram"] += 10.0

    return scores


# ═══════════════════════════════════════════════════════════════════════════════
# §13  KEYWORD-BASED AUTO-GROUPING
# ═══════════════════════════════════════════════════════════════════════════════

def _auto_group(entities: list[Entity]) -> list[tuple[str, list[str]]]:
    """Assign entities to semantic groups based on layer keywords."""
    assigned: dict[str, str] = {}

    for e in entities:
        name_lower = e.canonical.lower()
        best_group = None
        best_score = 0

        for group_name, keywords in _LAYER_KEYWORDS.items():
            for kw in keywords:
                if kw in name_lower:
                    score = len(kw)
                    if score > best_score:
                        best_score = score
                        best_group = group_name

        if best_group:
            assigned[e.canonical] = best_group
        else:
            assigned[e.canonical] = "Core Services"

    groups: dict[str, list[str]] = {}
    for entity_name, group_name in assigned.items():
        groups.setdefault(group_name, []).append(entity_name)

    return [(name, members) for name, members in groups.items() if members]


# ═══════════════════════════════════════════════════════════════════════════════
# §14  DYNAMIC TEXT-BASED GROUP DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_text_groups(
    text: str,
    entities: list[Entity],
) -> list[tuple[str, list[str]]]:
    """Extract groups from explicit text structure.

    Handles:
      - Headings followed by bullet items containing entities
      - "Label: entity1, entity2, entity3" colon-list patterns
    """
    entity_lower_map = {e.canonical.lower(): e.canonical for e in entities}
    groups: list[tuple[str, list[str]]] = []
    lines = text.split("\n")

    def _match_entity(fragment: str) -> str | None:
        fl = fragment.strip().lower()
        if fl in entity_lower_map:
            return entity_lower_map[fl]
        for el, ec in entity_lower_map.items():
            if len(fl) > 2 and (fl in el or el in fl):
                return ec
        return None

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Pattern 1: "## Heading" followed by bullet items
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().rstrip(":")
            items: list[str] = []
            j = i + 1
            while j < len(lines):
                nl = lines[j].strip()
                if not nl:
                    j += 1
                    continue
                if nl.startswith("#"):
                    break
                if not re.match(r"^[-*+•]\s+", nl) and nl[0:1].isalpha() and not nl[0:1].isspace():
                    break
                bm = re.match(r"^[-*+•]\s+(.+)", nl)
                if bm:
                    cleaned = _clean_bullet_item(bm.group(1))
                    hit = _match_entity(cleaned)
                    if hit and hit not in items:
                        items.append(hit)
                j += 1
            if len(items) >= 2:
                groups.append((heading, items))
            i = j
            continue

        # Pattern 2: "Label: item1, item2, item3"
        if ":" in stripped and not _ARROW_DELIM_RE.search(stripped):
            colon_idx = stripped.index(":")
            label = stripped[:colon_idx].strip()
            rest = stripped[colon_idx + 1:].strip()
            if rest and "," in rest and 1 < len(label.split()) <= 5:
                items = []
                for part in rest.split(","):
                    hit = _match_entity(part)
                    if hit and hit not in items:
                        items.append(hit)
                if len(items) >= 2:
                    groups.append((label, items))

        i += 1

    return groups


# ═══════════════════════════════════════════════════════════════════════════════
# §15  SYNTAX GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def _gen_architecture(
    entities: list[Entity],
    relationships: list[Relationship],
    text: str,
) -> str:
    """Generate architecture diagram syntax from extracted features."""
    lines_raw = text.strip().split("\n")
    title = "System Architecture"
    for line in lines_raw:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if len(candidate) > 2:
                title = candidate if len(candidate) <= 60 else candidate[:57].rsplit(" ", 1)[0]
                break
        elif not stripped.startswith(("-", "*", "+")) and not _ARROW_DELIM_RE.search(stripped):
            clean = stripped.rstrip(".:;,")
            if len(clean) <= 50:
                title = clean
            else:
                topic_match = re.match(
                    r"^(?:Our\s+|The\s+|A\s+|An\s+|We\s+have\s+a?\s*|"
                    r"This\s+is\s+a?\s*|Here\s+is\s+a?\s*)"
                    r"([\w\s&/.'-]+?)(?:\s+(?:consists?|has|have|uses?|is|was|"
                    r"includes?|contains?|with|deployed|running|that|which|"
                    r"built|designed|serving|handling|featuring)\b)",
                    clean, re.IGNORECASE,
                )
                if topic_match:
                    t = topic_match.group(1).strip()
                    title = _titlecase(t) if len(t) <= 60 else t[:57].rsplit(" ", 1)[0]
                else:
                    title = clean[:50].rsplit(" ", 1)[0]
            break

    # Deduplicate entities, keeping order
    seen: set[str] = set()
    ordered: list[str] = []
    for e in entities:
        if e.canonical not in seen:
            seen.add(e.canonical)
            ordered.append(e.canonical)

    if not ordered:
        return ""

    entity_set = set(ordered)

    # Build flow edges — only between known entities
    flow_lines: list[str] = []
    flow_seen: set[tuple[str, str]] = set()
    for rel in relationships:
        if rel.src in entity_set and rel.dst in entity_set:
            key = (rel.src, rel.dst)
            if key not in flow_seen:
                flow_seen.add(key)
                flow_lines.append(f"  {rel.src} -> {rel.dst}")

    # Groups: prefer explicit text groups, fall back to keyword-based
    text_groups = _detect_text_groups(text, entities)
    groups = text_groups if text_groups else _auto_group(entities)

    parts = [f"title: {title}", "", "services:"]
    for e in ordered:
        parts.append(f"  {e}")

    if flow_lines:
        parts.append("")
        parts.append("flow:")
        parts.extend(flow_lines)

    if groups and len(groups) > 1:
        parts.append("")
        parts.append("groups:")
        for gname, members in groups:
            valid = [m for m in members if m in entity_set]
            if valid:
                parts.append(f"  {gname}: {', '.join(valid)}")

    return "\n".join(parts)


def _gen_mindmap(hierarchy: HierarchyNode) -> str:
    """Generate mindmap syntax from hierarchy tree."""
    mm_lines = ["mindmap"]

    def _walk(node: HierarchyNode, depth: int) -> None:
        indent = "  " * (depth + 1)
        mm_lines.append(f"{indent}{node.text}")
        for child in node.children:
            _walk(child, depth + 1)

    _walk(hierarchy, 0)
    return "\n".join(mm_lines)


def _gen_flowchart(steps: list[Step]) -> str:
    """Generate Mermaid flowchart syntax from extracted steps."""
    fc_lines = ["flowchart TD"]
    node_ids: list[str] = []

    for i, step in enumerate(steps):
        nid = chr(65 + i) if i < 26 else f"N{i}"
        node_ids.append(nid)
        clean = re.sub(r"\*{1,3}|_{1,3}|`|~{2}", "", step.text).rstrip(".")
        clean = clean.replace('"', "'")

        if step.is_decision:
            fc_lines.append(f'    {nid}{{{clean}}}')
        else:
            fc_lines.append(f'    {nid}["{clean}"]')

    for i in range(len(node_ids) - 1):
        step = steps[i]
        if step.is_decision and i + 2 < len(node_ids):
            fc_lines.append(f"    {node_ids[i]} -->|Yes| {node_ids[i + 1]}")
            fc_lines.append(f"    {node_ids[i]} -->|No| {node_ids[i + 2]}")
        else:
            fc_lines.append(f"    {node_ids[i]} --> {node_ids[i + 1]}")

    return "\n".join(fc_lines)


def _gen_sequence(interactions: list[Interaction]) -> str:
    """Generate Mermaid sequence diagram syntax."""
    actors: list[str] = []
    seen: set[str] = set()
    for inter in interactions:
        for a in (inter.actor_from, inter.actor_to):
            if a not in seen:
                seen.add(a)
                actors.append(a)

    sq_lines = ["sequenceDiagram"]
    for a in actors:
        safe = re.sub(r"[^A-Za-z0-9_]", "_", a)
        sq_lines.append(f"    participant {safe} as {a}")

    for inter in interactions:
        src = re.sub(r"[^A-Za-z0-9_]", "_", inter.actor_from)
        dst = re.sub(r"[^A-Za-z0-9_]", "_", inter.actor_to)
        sq_lines.append(f"    {src}->>+{dst}: {inter.message}")

    return "\n".join(sq_lines)


def _gen_state(states: list[str], transitions: list[StateTransition]) -> str:
    """Generate Mermaid state diagram syntax."""
    st_lines = ["stateDiagram-v2"]

    if states and not transitions:
        for i in range(len(states) - 1):
            src = re.sub(r"[^A-Za-z0-9_]", "_", states[i])
            dst = re.sub(r"[^A-Za-z0-9_]", "_", states[i + 1])
            st_lines.append(f"    {src} --> {dst}")
        first = re.sub(r"[^A-Za-z0-9_]", "_", states[0])
        last = re.sub(r"[^A-Za-z0-9_]", "_", states[-1])
        st_lines.insert(1, f"    [*] --> {first}")
        st_lines.append(f"    {last} --> [*]")
    else:
        trans_states: list[str] = []
        for tr in transitions:
            src = re.sub(r"[^A-Za-z0-9_]", "_", tr.from_state)
            dst = re.sub(r"[^A-Za-z0-9_]", "_", tr.to_state)
            label = f": {tr.trigger}" if tr.trigger else ""
            st_lines.append(f"    {src} --> {dst}{label}")
            if src not in trans_states:
                trans_states.append(src)
            if dst not in trans_states:
                trans_states.append(dst)

        # Use provided states list order for initial state (preserves text order)
        if states:
            first = re.sub(r"[^A-Za-z0-9_]", "_", states[0])
        elif trans_states:
            first = trans_states[0]
        else:
            first = None
        if first:
            st_lines.insert(1, f"    [*] --> {first}")

    return "\n".join(st_lines)


def _gen_timeline(events: list[TimelineEvent]) -> str:
    """Generate Mermaid timeline syntax."""
    tl_lines = ["timeline", "    title Timeline"]
    for ev in events:
        tl_lines.append(f"    {ev.date} : {ev.description}")
    return "\n".join(tl_lines)


def _gen_er(er_features: dict) -> str:
    """Generate Mermaid ER diagram syntax from table entities."""
    tables = er_features.get("table_entities", [])
    if not tables:
        return ""

    er_lines = ["erDiagram"]
    entity_names: list[str] = []

    for table in tables:
        name = table["heading"] or f"Table{tables.index(table) + 1}"
        name = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_") or "Entity"
        entity_names.append(name)

        er_lines.append(f"    {name} {{")
        for row in table["rows"]:
            cells = [c.strip() for c in row.split("|") if c.strip()]
            if len(cells) >= 2:
                col_name = re.sub(r"[^A-Za-z0-9_]", "_", cells[0]).strip("_")
                col_type = re.sub(r"[^A-Za-z0-9_]", "_", cells[1]).strip("_") or "string"
                pk_marker = " PK" if any(
                    k in cells[0].lower() for k in ("id", "pk", "primary")
                ) else ""
                er_lines.append(f"        {col_type} {col_name}{pk_marker}")
        er_lines.append("    }")

    for i in range(len(entity_names) - 1):
        er_lines.append(f"    {entity_names[i]} ||--o{{ {entity_names[i + 1]} : references")

    return "\n".join(er_lines)


# ═══════════════════════════════════════════════════════════════════════════════
# §16  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def auto_analyze(text: str) -> tuple[str, str]:
    """Analyze raw text and return (diagram_type, diagram_syntax).

    The analyzer deeply scans the input for:
      - Technology names, services, and components
      - Relationships and data flows between them
      - Hierarchical structures (headings, bullets, categories)
      - Sequential processes and decision points
      - Actor-to-actor interactions (request/response)
      - State machines and transitions
      - Timeline events and milestones
      - Entity-attribute-relationship data models

    It scores each diagram type, picks the best fit, and generates
    the complete diagram syntax ready for rendering.
    """
    text = _normalize(text)
    if not text:
        return "mindmap", "mindmap\n  Empty"

    lines = text.split("\n")
    sentences = _split_sentences(text)
    structure = _detect_structure(lines)

    # Extract features for every diagram type
    entities = _extract_entities(text, sentences)
    relationships = _extract_relationships(text, sentences, entities)
    hierarchy = _extract_hierarchy(lines)
    steps = _extract_steps(text, lines, sentences)
    interactions = _extract_interactions(text, sentences)
    states, transitions = _extract_states(text, sentences)
    timeline_events = _extract_timeline(text, lines)
    er_features = _extract_er_features(text, lines)
    _, _, arrow_msg_lines = _extract_arrow_chains(text)

    # Score
    scores = _score_types(
        entities, relationships, hierarchy, steps,
        interactions, states, transitions,
        timeline_events, er_features, structure,
        arrow_msg_lines=arrow_msg_lines,
    )

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    # Fallback: if all scores are very low, default to mindmap from hierarchy
    if best_score < 5.0:
        if hierarchy and _count_tree_nodes(hierarchy) >= 3:
            best_type = "mindmap"
        elif len(entities) >= 2:
            best_type = "architecture"
        else:
            best_type = "mindmap"

    # Generate syntax for the winning type
    syntax = ""

    if best_type == "architecture":
        syntax = _gen_architecture(entities, relationships, text)
        if not syntax:
            if hierarchy:
                best_type = "mindmap"
                syntax = _gen_mindmap(hierarchy)

    elif best_type == "mindmap":
        if hierarchy:
            syntax = _gen_mindmap(hierarchy)
        else:
            title = "Overview"
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    title = stripped.lstrip("#").strip()
                    break
            groups = _auto_group(entities)
            mm = ["mindmap", f"  {title}"]
            if len(groups) > 1:
                for gname, members in groups:
                    mm.append(f"    {gname}")
                    for m in members[:8]:
                        mm.append(f"      {m}")
            else:
                for e in entities[:20]:
                    mm.append(f"    {e.canonical}")
            syntax = "\n".join(mm)

    elif best_type == "flowchart":
        syntax = _gen_flowchart(steps)

    elif best_type == "sequenceDiagram":
        syntax = _gen_sequence(interactions)

    elif best_type == "stateDiagram-v2":
        syntax = _gen_state(states, transitions)

    elif best_type == "timeline":
        syntax = _gen_timeline(timeline_events)

    elif best_type == "erDiagram":
        syntax = _gen_er(er_features)

    if not syntax:
        if hierarchy and _count_tree_nodes(hierarchy) >= 3:
            best_type = "mindmap"
            syntax = _gen_mindmap(hierarchy)
        elif len(entities) >= 2:
            best_type = "architecture"
            syntax = _gen_architecture(entities, relationships, text)
        else:
            best_type = "mindmap"
            mm_lines = ["mindmap", "  Content"]
            for sent in sentences[:20]:
                clean = sent[:60].strip()
                if clean:
                    mm_lines.append(f"    {clean}")
            syntax = "\n".join(mm_lines)

    return best_type, syntax
