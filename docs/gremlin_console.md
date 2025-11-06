# Connect Gremlin Console to your AGS VM

Use the Apache TinkerPop Gremlin Console to run ad‑hoc traversals against your AGS.

1. Install Gremlin Console on your workstation

```bash
curl -LO https://archive.apache.org/dist/tinkerpop/3.6.4/apache-tinkerpop-gremlin-console-3.6.4-bin.zip
unzip apache-tinkerpop-gremlin-console-3.6.4-bin.zip
cd apache-tinkerpop-gremlin-console-3.6.4
```

2. Create a remote configuration YAML pointing to your AGS external IP
   Create `conf/graph-remote.yaml` with the following contents (adjust IP/port as needed):

```yaml
hosts: [ "<AGS_EXTERNAL_IP>" ]
port: 8182
serializer:
  {
    className: org.apache.tinkerpop.gremlin.util.serializer.GraphBinaryMessageSerializerV1,
    config: { ioRegistries: [ ] },
  }
connectionPool:
  {
    enableSsl: false,
    maxInProcessPerConnection: 64,
    maxSimultaneousUsagePerConnection: 64,
    minConnectionPoolSize: 8,
    maxConnectionPoolSize: 64,
  }
channelizer: org.apache.tinkerpop.gremlin.server.channel.WsAndHttpChannelizer
```

Notes:

- For multiple AGS instances, list all IPs: `hosts: [ "10.0.0.10", "10.0.0.11" ]` (client round‑robins).
- If AGS is fronted by TLS (HTTPS/WSS), set `enableSsl: true` and ensure certificates are trusted.

3. Connect and run traversals

```bash
./bin/gremlin.sh
gremlin> :remote connect tinkerpop.server conf/graph-remote.yaml
gremlin> :remote console
gremlin> g.V().limit(5).valueMap(true)
```

If you maintain separate endpoints for admin and main graphs, create additional YAML files (e.g.,
`conf/graph-admin.yaml`) and connect accordingly.