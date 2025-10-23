# Deployment Setup for Fraud Detection Demo with Aerospike Graph Service (AGS)

mvn spring-boot:run -Dspring-boot.run.profiles=cli

This guide walks through a production-style deployment of the demo on GCP using Aerospike Database, Aerospike Graph Service (AGS), and the fraud-detection Java backend/frontend.

Prereqs

- GCP project with billing enabled and IAM perms to manage GCS, Compute Engine, Firewall
- Docker and Docker Compose locally (for testing) or on VMs
- aerolab installed (to provision Aerospike nodes)
- Java 17+, Maven, Node.js 18+ (if building from source)
- gsutil, gcloud CLI

Docs reference

- AGS docs: `https://docs.aerospike.com/enterprise/graph`
- Aerospike server: `https://docs.aerospike.com/server`
- aerolab: `https://github.com/aerospike/aerolab`

---

# Upload bulkloader data, jar, and properties to a GCP bucket

1. Create a GCS bucket

```bash
gcloud storage buckets create gs://<YOUR_BUCKET> --location=<REGION>
```

2. Build/upload artifacts

- Java backend JAR (`java-backend/target/fraud-detection-backend-*.jar`)
- Bulkloader CSV/JSON data (`data/graph_csv` and `data/users*.json` if needed)
- AGS config (if customized)

```bash
gsutil -m cp -r data/graph_csv gs://<YOUR_BUCKET>/bulkload/
gsutil cp java-backend/target/fraud-detection-backend-*.jar gs://<YOUR_BUCKET>/artifacts/
gsutil cp docs/*.properties gs://<YOUR_BUCKET>/config/ || true
```

3. Make bucket readable by your deployment service account or VM service accounts

```bash
gsutil iam ch serviceAccount:<SA>@<PROJECT>.iam.gserviceaccount.com:objectViewer gs://<YOUR_BUCKET>
```

---

# Spin up Aerospike nodes via aerolab

1. Install aerolab and login

```bash
aerolab version
```

2. Create a 2-node Aerospike cluster

```bash
aerolab cluster create -n asdb -c 3 -e enterprise -s 8 -r 32 -o ubuntu22
# open ports 3000-3002 and any exporter ports if needed
aerolab cluster attach -n asdb -- bash -lc "asinfo -v build"  # sanity check
```

3. Configure namespace (SSD vs memory-mode) as per your performance targets. Use aerolab templates or copy a custom `aerospike.conf`:

```bash
aerolab conf apply -n asdb -f ./conf/aerospike.conf
aerolab cluster restart -n asdb
```

---

# Spin up Graph VMs

1. Create an AGS VM and a Client VM (Next.js + backend), pick machine types to match goals

```bash
gcloud compute instances create graph-vm \
  --machine-type=n2-highcpu-8 --image-family=debian-12 --image-project=debian-cloud \
  --scopes=storage-ro,compute-rw --tags=ags,http-server,https-server

gcloud compute instances create client-vm \
  --machine-type=n2-standard-8 --image-family=debian-12 --image-project=debian-cloud \
  --scopes=storage-ro,compute-rw --tags=http-server,https-server
```

2. Open firewall ports (AGS HTTP/Gremlin and client)

```bash
gcloud compute firewall-rules create allow-ags --allow tcp:8182,tcp:9090 \
  --target-tags=ags --direction=INGRESS
```

3. Install Docker on both VMs

```bash
sudo apt-get update && sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
```

---

# Start AGS

```bash
sudo docker run -d --name asgraph \
  -p 8182:8182 -p 9090:9090 \
  -e AEROSPIKE_CLIENT_HOST=<AEROSPIKE_NODE_IP> \
  -e AEROSPIKE_CLIENT_NAMESPACE=test \
  aerospike/aerospike-graph-service:latest
```

Health check

```bash
curl -s http://<GRAPH_VM>:9090/healthcheck
```

---

# L3 BulkLoader Data

1. Download bulkload CSVs from GCS to AGS VM (or mount GCS FUSE)

```bash
gsutil -m cp -r gs://<YOUR_BUCKET>/bulkload/ ./bulkload
```

2. Create indexes (recommended prior to load and queries). Use AGS admin API or prebuilt scripts.

3. Run bulk loader (AGS supports L3 bulkload endpoints or Gremlin admin calls depending on build)
   Example (pseudo):

```bash
curl -X POST "http://<GRAPH_VM>:9090/bulkload" \
  -H "Content-Type: application/json" \
  -d '{"verticesPath":"/home/ubuntu/bulkload/vertices","edgesPath":"/home/ubuntu/bulkload/edges"}'
```

Monitor

```bash
watch -n 2 curl -s http://<GRAPH_VM>:9090/healthcheck
```

---

## Configure bulkload script with your GCP data

If you use a helper script, set:

```bash
export GCS_BUCKET=<YOUR_BUCKET>
export VERTICES_PATH=gs://$GCS_BUCKET/bulkload/vertices
export EDGES_PATH=gs://$GCS_BUCKET/bulkload/edges
export AGS_HOST=<GRAPH_VM>
export AGS_PORT=9090
```

Then invoke your script to copy and kick off bulk load.

---

# Start CLI

The repo includes a Java CLI to query performance metrics and rules.
```bash
gcloud compute instances create client-vm \
  --machine-type=n2-standard-8 --image-family=debian-12 --image-project=debian-cloud \
  --scopes=storage-ro,compute-rw --tags=client,backend,frontend
```

Now on the VM:
1. Install dependencies
```bash
sudo apt update
sudo apt install git
sudo apt install maven
wget https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.deb
update-alternatives --list java || true
update-alternatives --list javac || true
sudo apt install ./jdk-21_linux-x64_bin.deb 
```

2. Clone the repository
```bash
git clone https://github.com/aerospike-examples/graph-fraud-demo.git
git checkout graph-fraud-demo/
git checkout java
mvn install package 
```

3. Update Application Properties
Update this with settings, for example set the hosts to the Internal IPs of the graph instances you created
```bash
nano java-backend/src/java/resources/application.properties 
```

4. Run the CLI pointing at AGS

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=cli
```

3. Useful commands

- stats: check indexes and counts
- start #: Starts generator at given amount
- stop: Stops the generator
---

Appendix: Backend/Frontend

- Backend (Spring Boot)
  - Copy JAR to client VM and create a systemd unit or run via Docker.
  - Config: `graph.gremlin-host=<GRAPH_VM>`, `graph.gremlin-port=8182`, pools set to 64–128.
- Frontend (Next.js)
  - Deploy Next 15 server on port 3001, behind Caddy/nginx.
  - Proxy `/api/*` and `/swagger-ui/*` to backend, everything else to Next.

Troubleshooting

- If TPS plateaus early: raise connection/workers on client and AGS; check indexes.
- If latency drifts after 60–90s: inspect AGS GC logs, adjust heap and G1 settings; ensure server worker pools and request limits are sufficient.

---

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
hosts: ["<AGS_EXTERNAL_IP>"]
port: 8182
serializer:
  {
    className: org.apache.tinkerpop.gremlin.util.serializer.GraphBinaryMessageSerializerV1,
    config: { ioRegistries: [] },
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

If you maintain separate endpoints for admin and main graphs, create additional YAML files (e.g., `conf/graph-admin.yaml`) and connect accordingly.
