# Uptime Monitor 

Click [here](http://{{.nuon.install.sandbox.outputs.nuon_dns.public_domain.name}}) to see your instance.

## Headlamp Dashboard

Access the Kubernetes dashboard at [/headlamp](http://{{.nuon.install.sandbox.outputs.nuon_dns.public_domain.name}}/headlamp/)

**Authentication Token:**
```
{{ .nuon.actions.workflows.headlamp_token.outputs.steps.create.token }}
```

## Full State

<details>
  <summary>Full Install State</summary>
  <pre>{{ toPrettyJson .nuon }}</pre>
</details>
