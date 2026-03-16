"""One-time script to download curated SVG icons from Iconify API into src/static/icons/.

Usage:
    python download_icons.py

Each icon is saved as {local_name}.svg so that icon_registry.py auto-detects them
via the KEYWORD_ICON_MAP file-name matching.
"""

import urllib.request
import time
from pathlib import Path

ICONS_DIR = Path(__file__).resolve().parent / "src" / "static" / "icons"

ICONIFY_ICONS: dict[str, str] = {
    # --- Databases ---
    "database":       "mdi/database",
    "postgres":       "logos/postgresql",
    "mysql":          "logos/mysql",
    "mongodb":        "logos/mongodb-icon",
    "redis":          "logos/redis",
    "sqlite":         "devicon/sqlite",
    "dynamodb":       "logos/aws-dynamodb",
    "cockroachdb":    "simple-icons/cockroachlabs",
    "elasticsearch":  "logos/elasticsearch",

    # --- Containers & Orchestration ---
    "docker":         "logos/docker-icon",
    "kubernetes":     "logos/kubernetes",
    "podman":         "devicon/podman",

    # --- Cloud Providers ---
    "aws":            "logos/aws",
    "azure":          "logos/microsoft-azure",
    "gcp":            "logos/google-cloud",
    "cloudflare":     "logos/cloudflare-icon",
    "vercel":         "logos/vercel-icon",
    "heroku":         "logos/heroku-icon",
    "digitalocean":   "logos/digital-ocean",

    # --- CI/CD & DevOps ---
    "jenkins":        "logos/jenkins",
    "github-actions": "logos/github-actions",
    "gitlab":         "logos/gitlab",
    "terraform":      "logos/terraform-icon",
    "ansible":        "logos/ansible",
    "circleci":       "logos/circleci",

    # --- Messaging & Queues ---
    "kafka":          "logos/kafka-icon",
    "rabbitmq":       "logos/rabbitmq-icon",
    "nats":           "logos/nats-icon",

    # --- Web & Frontend ---
    "nginx":          "logos/nginx",
    "react":          "logos/react",
    "nextjs":         "logos/nextjs-icon",
    "vue":            "logos/vue",
    "angular":        "logos/angular-icon",
    "svelte":         "logos/svelte-icon",

    # --- Backend & Languages ---
    "nodejs":         "logos/nodejs-icon",
    "python":         "logos/python",
    "go":             "logos/go",
    "java":           "logos/java",
    "rust":           "logos/rust",
    "dotnet":         "logos/dotnet",

    # --- Security & Auth ---
    "auth":           "mdi/shield-lock",
    "oauth":          "logos/oauth",
    "vault":          "logos/vault-icon",
    "lock":           "mdi/lock",
    "firewall":       "mdi/wall-fire",

    # --- Monitoring & Observability ---
    "prometheus":     "logos/prometheus",
    "grafana":        "logos/grafana",
    "datadog":        "logos/datadog",
    "sentry":         "logos/sentry-icon",
    "elastic":        "logos/elastic-icon",
    "newrelic":       "simple-icons/newrelic",

    # --- Storage & CDN ---
    "s3":             "logos/aws-s3",
    "storage":        "mdi/cloud-upload",
    "cdn":            "mdi/earth",

    # --- Generic / Common ---
    "server":         "mdi/server",
    "api":            "mdi/api",
    "gateway":        "mdi/gate",
    "load-balancer":  "mdi/scale-balance",
    "user":           "mdi/account-circle",
    "mobile":         "mdi/cellphone",
    "web":            "mdi/web",
    "email":          "mdi/email",
    "notification":   "mdi/bell",
    "function":       "mdi/lambda",
    "lambda":         "logos/aws-lambda",
    "microservice":   "mdi/hexagon-multiple",
    "cache":          "mdi/memory",
    "dns":            "mdi/dns",
    "globe":          "mdi/earth",
    "network":        "mdi/lan",
    "vpn":            "mdi/vpn",
    "webhook":        "mdi/webhook",
    "graphql":        "logos/graphql",
    "grpc":           "logos/grpc",
    "mqtt":           "simple-icons/mqtt",

    # --- AI/ML ---
    "ml":             "mdi/brain",
    "ai":             "mdi/robot",
    "tensorflow":     "logos/tensorflow",
    "pytorch":        "logos/pytorch-icon",
    "openai":         "simple-icons/openai",

    # --- Data & Analytics ---
    "spark":          "logos/apache-spark",
    "airflow":        "logos/airflow-icon",
    "snowflake":      "logos/snowflake-icon",
    "bigquery":       "logos/google-bigquery",
    "dashboard":      "mdi/view-dashboard",
    "analytics":      "mdi/chart-bar",

    # --- Misc ---
    "git":            "logos/git-icon",
    "github":         "logos/github-icon",
    "slack":          "logos/slack-icon",
    "jira":           "logos/jira",
    "stripe":         "logos/stripe",
    "twilio":         "logos/twilio-icon",
    "consul":         "logos/consul",
    "etcd":           "logos/etcd",
    "istio":          "logos/istio",
    "envoy":          "logos/envoy",
    "linkerd":        "simple-icons/linkerd",
}

ICONIFY_API = "https://api.iconify.design"


def download_icon(local_name: str, iconify_id: str) -> bool:
    url = f"{ICONIFY_API}/{iconify_id}.svg"
    dest = ICONS_DIR / f"{local_name}.svg"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clarity-beta/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            svg_data = resp.read().decode("utf-8")

        if not svg_data.strip().startswith("<svg"):
            print(f"  SKIP  {local_name:20s} <- {iconify_id} (not valid SVG)")
            return False

        dest.write_text(svg_data, encoding="utf-8")
        print(f"  OK    {local_name:20s} <- {iconify_id}")
        return True

    except Exception as e:
        print(f"  FAIL  {local_name:20s} <- {iconify_id} ({e})")
        return False


def main():
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    total = len(ICONIFY_ICONS)
    ok = 0
    fail = 0

    print(f"\nDownloading {total} icons from Iconify API into:\n  {ICONS_DIR}\n")

    for i, (local_name, iconify_id) in enumerate(ICONIFY_ICONS.items(), 1):
        print(f"[{i:3d}/{total}]", end="")
        if download_icon(local_name, iconify_id):
            ok += 1
        else:
            fail += 1
        if i % 10 == 0:
            time.sleep(0.3)

    print(f"\nDone: {ok} downloaded, {fail} failed, {total} total")
    print(f"Icons saved to: {ICONS_DIR}")


if __name__ == "__main__":
    main()
