# Configuring Glance

Glance's layout and widgets are defined in a single YAML file:
`applications/vendor/glance/config/glance.yml`. This file is mounted
into the pod as a ConfigMap — edit it, push to `main`, and ArgoCD
applies the change automatically (Glance reloads on restart).

## Config structure

```yaml
server:
  port: 8080

pages:
  - name: Home
    columns:
      - size: small   # or: full
        widgets:
          - type: calendar
          # ...
```

Columns accept `small` or `full` for size. Widgets are listed under
each column in order.

## Pages

Glance supports multiple pages, accessible from a nav tab at the top.
The dashboard currently has two:

| Page | Slug | Purpose |
| --- | --- | --- |
| Home | *(default)* | General use — calendar, events, services |
| Home-lab | `home-lab` | Technical — Kubernetes apps, nodes, DNS stats |

To add a new page:

```yaml
pages:
  - name: Home
    columns: [...]
  - name: Media
    slug: media      # sets the URL fragment: neustrom.net/#media
    columns: [...]
```

If `slug` is omitted, Glance derives it from the name.

## Environment variable injection

Glance supports `${ENV_VAR}` substitution anywhere in the config file.
Two variables are injected from the `glance-secrets` SealedSecret:

| Variable | Purpose |
| --- | --- |
| `ICS_URL` | ICS feed URL for the calendar events widget |
| `PIHOLE_TOKEN` | Pi-hole v6 password for the DNS stats widget |

To add a new secret value, add the key to the `.env` file, re-seal,
and reference it as `${YOUR_KEY}` in `glance.yml`.

## Icons

Icons can come from several sources, selected by prefix:

| Prefix | Library | Example |
| --- | --- | --- |
| `si:` | [Simple Icons](https://simpleicons.org/) | `si:pihole` |
| `sh:` | [selfh.st icons](https://selfh.st/icons/) | `sh:glance` |
| `di:` | [Dashboard Icons](https://github.com/homarr-labs/dashboard-icons) | `di:argocd` |
| `mdi:` | [Material Design Icons](https://pictogrammers.com/library/mdi/) | `mdi:camera` |

You can also use a direct URL to any image:

```yaml
icon: https://example.com/path/to/icon.png
```

For icons that don't automatically adapt to light/dark mode, prefix
with `auto-invert` to have Glance invert the colours based on the
active theme (expects black icons on a transparent background):

```yaml
icon: auto-invert https://example.com/black-icon.png
icon: auto-invert sh:glance-dark
```

Icons from Simple Icons and Material Design Icons adapt to the theme
automatically without this prefix.

## Widget reference

### Calendar

Built-in month view. No external data needed.

```yaml
- type: calendar
  first-day-of-week: monday
```

### To-do

Persistent to-do list stored in Glance's local state. The `id` field
namespaces the list so multiple to-do widgets on the same page don't
collide.

```yaml
- type: to-do
  id: main
```

!!! info "To-do storage is browser-local"
    The to-do widget stores its data in the browser's `localStorage` — nothing
    is written to the cluster. Items persist across pod restarts but are
    per-browser and per-device. Clearing browser data or using a different
    browser will show an empty list.

### Monitor

Displays a list of services with live up/down status. Use `check-url`
to point at the internal Kubernetes service so health checks don't
round-trip through the public internet or require authentication.

```yaml
- type: monitor
  title: Services
  sites:
    - title: Pi-hole
      url: https://pihole.neustrom.net          # clickable link shown to user
      check-url: http://pihole-web.pihole.svc.cluster.local  # internal health check
      icon: si:pihole
```

The `url` and `check-url` are independent — `url` is what the user
clicks, `check-url` is silently polled. Omitting `check-url` means
`url` is used for both.

If a service returns a non-200 that should still be considered healthy,
list the accepted codes with `alt-status-codes`. The site will show as
online but with a warning indicator rather than a full green status:

```yaml
sites:
  - title: Pi-hole
    url: https://pihole.neustrom.net
    check-url: http://pihole-web.pihole.svc.cluster.local/api/info/version
    icon: si:pihole
    alt-status-codes:
      - 403
```

To show only failing services:

```yaml
- type: monitor
  show-failing-only: true
  sites: [...]
```

### iCal events (`custom-api`)

Fetches events from the iCal sidecar running at `localhost:8076`.
The sidecar proxies the ICS feed and returns structured JSON.

```yaml
- type: custom-api
  title: Calendar Events
  cache: 15m
  url: http://localhost:8076/events
  parameters:
    url: ${ICS_URL}   # injected from secret
    limit: 5
  template: |
    # ... Go template rendering the events JSON
```

Useful parameters:

| Parameter | Default | Description |
| --- | --- | --- |
| `limit` | all | Max upcoming events to return |
| `lookback_days` | 14 | Days back to include already-started events |
| `horizon_days` | 3650 | Days forward to look |

### Kubernetes apps & nodes (`extension`)

Served by the `glance-k8s` service running in the same namespace.
The widget renders whatever HTML that service returns.

```yaml
- type: extension
  title: Kubernetes Apps
  url: http://glance-k8s/extension/apps
  allow-potentially-dangerous-html: true
  cache: 30s
  parameters:
    show-if: |
      namespace != "kube-system"

- type: extension
  title: Kubernetes Nodes
  url: http://glance-k8s/extension/nodes
  allow-potentially-dangerous-html: true
  cache: 30s
```

The `show-if` parameter accepts [expr-lang](https://expr-lang.org/)
expressions. Available fields: `namespace`, `name`, and any annotation
values.

#### Annotating workloads

Workloads show up with their Kubernetes name by default. Override the
display with annotations:

```yaml
metadata:
  annotations:
    glance/name: "My App"
    glance/icon: "si:myapp"
    glance/url: "https://myapp.neustrom.net"
```

Group related workloads (e.g. a server + worker) under one entry:

```yaml
# Parent workload
annotations:
  glance/id: "myapp"

# Child workload
annotations:
  glance/parent: "myapp"
```

### Pi-hole DNS stats

Uses Pi-hole v6's password-based API. The `password` field accepts
the plain admin password (injected via `${PIHOLE_TOKEN}`).

```yaml
- type: dns-stats
  service: pihole-v6
  url: http://pihole-web.pihole.svc.cluster.local
  password: ${PIHOLE_TOKEN}
```

!!! note "Pi-hole v6 service type"
    Use `service: pihole-v6`, not `pihole`. The built-in `pihole` type
    targets the v5 API (`/admin/api.php`) which does not exist in v6.

## Custom API widget

The `custom-api` widget fetches JSON from any HTTP endpoint and renders
it using Go templates. It's the main tool for integrating services that
don't have a built-in Glance widget.

### Basic structure

```yaml
- type: custom-api
  title: My Widget
  url: https://api.example.com/data
  cache: 5m
  template: |
    {{ .JSON.String "title" }}
```

### Accessing JSON

```yaml
template: |
  {{ .JSON.String "name" }}           # string field
  {{ .JSON.Int "count" }}             # integer field
  {{ .JSON.Bool "active" }}           # boolean field
  {{ .JSON.String "user.address" }}   # nested field (dot notation)
  {{ .JSON.String "items.0.name" }}   # array index
```

Iterating over an array:

```yaml
template: |
  {{ range .JSON.Array "posts" }}
    {{ .String "title" }}
  {{ end }}
```

For primitive arrays (array of strings/numbers), use an empty key:

```yaml
template: |
  {{ range .JSON.Array "" }}
    {{ .String "" }}
  {{ end }}
```

Use `.StringOr "field" "fallback"` (and `IntOr`, `BoolOr`) for safe
defaults when a field may be absent.

### Time functions

```yaml
template: |
  {{ $t := .JSON.String "created_at" | parseTime "rfc3339" }}
  {{ $t | formatTime "Mon, 02 Jan 2006" }}
  <span {{ $t | toRelativeTime }}></span>   # renders as "2h ago", "in 3d", etc.
```

`parseTime` accepts: `rfc3339`, `datetime`, or any Go time layout string.

### Chained requests

Make a secondary request inside the template using data from the first:

```yaml
template: |
  {{ $detail := newRequest "https://api.example.com/items"
     | withParameter "id" (.JSON.String "id")
     | withHeader "Authorization" "Bearer token"
     | getResponse
  }}
  {{ $detail.JSON.String "description" }}
```

### Parameters & headers

Pass query parameters and headers from config (avoids putting secrets
in the template):

```yaml
- type: custom-api
  url: https://api.example.com/data
  parameters:
    key: value
  headers:
    Authorization: Bearer ${MY_TOKEN}
```

### HTTP response access

```yaml
template: |
  {{ if eq .Response.StatusCode 200 }}ok{{ end }}
  {{ .Response.Header.Get "Content-Type" }}
```

## Extensions

Extensions are external HTTP services that return HTML for Glance to
embed. They use a small set of response headers to communicate metadata
back to Glance.

### Widget config

```yaml
- type: extension
  url: http://my-service.my-namespace.svc.cluster.local/widget
  allow-potentially-dangerous-html: true  # required for HTML content
  cache: 30s
  parameters:
    some-param: value
```

Parameters are appended as query parameters to the URL.

### Response headers

The service controls the widget's appearance via response headers:

| Header | Purpose |
| --- | --- |
| `Widget-Title` | Widget title (defaults to "Extension") |
| `Widget-Title-URL` | URL opened when the title is clicked |
| `Widget-Content-Type` | Content type — currently only `html` is supported |
| `Widget-Content-Frameless` | Set to `true` to remove the background frame |

### Glance CSS classes

Extensions can reuse Glance's built-in CSS classes for consistent
styling across themes:

| Class | Purpose |
| --- | --- |
| `color-primary`, `color-highlight`, `color-positive`, `color-negative`, `color-subdue` | Text colours |
| `size-h1` … `size-h6`, `size-base` | Font sizes |
| `list`, `list-gap-10`, `list-with-separator` | List layout |
| `collapsible-container` + `data-collapse-after="N"` | Collapse items after N entries |

!!! warning "Class name stability"
    Glance's CSS class names may change between versions. Extensions
    using them need to be updated when upgrading Glance.

### glance-k8s

[glance-k8s](https://github.com/lukasdietrich/glance-k8s) is deployed
as a separate service in the `glance` namespace and serves two
extension endpoints:

| Endpoint | Shows |
| --- | --- |
| `/extension/apps` | Deployments, StatefulSets, DaemonSets across namespaces |
| `/extension/nodes` | Node resource usage (CPU, memory) |

See [Kubernetes apps & nodes](#kubernetes-apps--nodes-extension) above
for the widget config and workload annotation reference.

## Updating secrets

If the ICS URL or Pi-hole password changes:

1. Update the `.env` file with the new values
2. Run `mise run seal-secret` (namespace: `glance`, secret name: `glance-secrets`)
3. Replace `applications/vendor/glance/glance-secrets-sealedsecret.yaml`
4. Push — ArgoCD will update the secret and restart Glance
