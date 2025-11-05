# Deployment Setup for Fraud Detection Demo with Aerospike Graph Service (AGS)

This guide walks through a production-style deployment of the demo on GCP using Aerospike Database, Aerospike Graph
Service (AGS), and the fraud-detection Java backend/frontend.

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

# Spin up Aerospike nodes via Aerolab

1. Install aerolab and login, configuring for GCP `https://github.com/aerospike/aerolab/blob/master/docs/direnv.md`

```bash
aerolab version
```

2. Create a 2-node Aerospike cluster with Aerolab

Configure the variables for cluster creation in **[this script](./scripts/set_variables.sh)**
Then, create the Aerospike DB cluster using this script, which takes variables from the first:
```bash
./aerolab.sh
```

---

# Spin up Graph VMs

1. Create 1 or more AGS VM's and a Client VM (Next.js + backend), pick machine types to match goals

```bash
gcloud compute instances create graph-vm \
  --machine-type=n2-highcpu-8 --image-family=debian-12 --image-project=debian-cloud \
  --scopes=storage-ro,compute-rw --tags=ags,http-server,https-server
```

2. Open firewall ports (AGS HTTP/Gremlin and client)

```bash
gcloud compute firewall-rules create allow-ags --allow tcp:8182,tcp:9090 \
  --target-tags=ags --direction=INGRESS
```

3. Install Docker on both AGS VMs

```bash
sudo apt-get update && sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
```

---

# Start AGS
Make sure you set `<AEROSPIKE_NODE_IPS>` to your aerolab IPs like `10.128.0.3, 10.128.0.4`.
If you don't know them, use 
```bash
   aerolab cluster list
```
```bash
sudo docker run -d --name asgraph \
  -p 8182:8182 \
  -e aerospike.client.host=<AEROSPIKE_NODE_IPS> \
  -e aerospike.client.batch-threshold.per-node="1" \
  -e aerospike.client.namespace=test \
  aerospike/aerospike-graph-service:latest
```

Check the logs to make sure it started correctly:
```bash
   docker logs ags --tail 150
```

---

# Setup the application

Create a VM for the client:

```bash
gcloud compute instances create client-vm \
  --machine-type=n2-standard-8 --image-family=debian-12 --image-project=debian-cloud \
  --scopes=storage-ro,compute-rw --tags=http-server,https-server
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
sudo apt install npm
sudo apt install nodejs
```

2. Clone the repository

```bash
mkdir /var/www
cd /var/www
git clone https://github.com/aerospike-examples/graph-fraud-demo.git
cd graph-fraud-demo/java-backend
```

3. Update Application Properties
   Update this with settings, for example set the hosts to the Internal IPs of the graph instances you created, and the
   `metadata.aerospikeAddress` to one of your Aerospike Nodes internal IPs

```bash
nano java-backend/src/main/resources/application.properties
```

# L3 BulkLoader Data

## Upload bulkloader data, jar, and properties to a GCP bucket

1. Create a GCS bucket

```bash
gcloud storage buckets create gs://<YOUR_BUCKET> --location=<REGION>
```

2. Build/upload artifacts to GCP bucket

- Latest Bulkloader JAR (`https://aerospike.com/download/graph/loader/`)
- Bulkloader CSV/JSON data (`data/graph_csv` and `data/users*.json` if needed)
- AGS config (if customized)

```bash
gsutil -m cp -r data/graph_csv gs://<YOUR_BUCKET>/bulkload/
gsutil cp bulk-load.jar gs://<YOUR_BUCKET>/artifacts/
gsutil cp docs/*.properties gs://<YOUR_BUCKET>/config/ || true
```

3. Make bucket readable by your deployment service account or VM service accounts

```bash
gsutil iam ch serviceAccount:<SA>@<PROJECT>.iam.gserviceaccount.com:objectViewer gs://<YOUR_BUCKET>
```

## Configure bulkload script with your GCP data

Set the following variables in `java-backend/src/main/resources/l3-bulkload.sh`:

```bash
dataproc_name="<Dataproc-cluster-name>"
region=us-central1
zone=us-central1-a
instance_type=n2d-highmem-8
num_workers=8
project=<Your-GCP-Project-Name>
bulk_jar_uri="gs://<Your-GCP-Bucket>/<path-to-bulkload-jar>"
```

Then invoke the script to kick off bulk load.

---

# Testing / Running

If you want a quick way to test the backend, start the CLI with

```bash
cd java-backend
mvn spring-boot:run -Dspring-boot.run.profiles=cli
```

_Useful commands_

- stats: check indexes and counts
- start #: Starts generator at given amount
- stop: Stops the generator

If you want to test out the frontend as well, navigate to the frontend and run the dev:

```bash
cd ../frontend
npm run dev
```

If you would like to deploy this, refer to the `deployment.md` file in the docs.

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
