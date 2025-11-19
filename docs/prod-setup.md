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
- Aerolab: `https://github.com/aerospike/aerolab`

---

# Spin up Aerospike nodes via Aerolab

1. Install aerolab and login, configuring for GCP **[with this guide](https://github.com/aerospike/aerolab/blob/master/docs/gcp-setup.md)**

```bash
aerolab version
```

2. Create a 2-node Aerospike cluster with Aerolab

Configure the variables for cluster creation in **[this script](../scripts/deployment/set_variables.sh)**
Then, create the Aerospike DB cluster using this script, which takes variables from the first:
```bash
./aerolab.sh
```

---

# Spin up Graph VMs

1. Create 1 or more AGS VM's and a Client VM (Next.js + backend), pick machine types to match goals
Since AGS is stateless, each instance of AGS does not need to know each other, so you can repeat these steps for each
instance you would like to create.
**NOTE** Arm CPUs have been found to perform significantly better with AGS, for production if your application
is latency sensitive, consider using the C4A family of machines in GCP:

```bash
gcloud compute instances create fraud-demo-graph\
  --machine-type=<GCP_INSTANCE_TYPE> --image-family=debian-12 --image-project=debian-cloud \
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
Make sure you set `<AEROSPIKE_NODE_IPS>` to your aerolab IPs, like `10.128.0.3, 10.128.0.4`.
If you don't know them, use 
```bash
   aerolab cluster list
```

Now start AGS on your graph VM
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
  --machine-type=<GCP_INSTANCE_TYPE> --image-family=debian-12 --image-project=debian-cloud \
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
cd graph-fraud-demo
git checkout java
cd java-backend
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

2. Generate data into your GCP bucket:
In your client VM, in the cloned repo, make a python venv and install the requirements
```bash
  python -m venv venv 
  .\venv\Scripts\activate
  pip install -r ./scripts/requirements.txt
```
This script will generate the data needed and transfer it into your GCP bucket.
If you want to keep it locally as well, remove the `--gcs-delete-local` from the command:

**NOTE** Your current user must be authorized to place files in the GCP bucket
```bash
python3 ./scripts/generate_user_data_gcp.py \
  --users 20000 --region american \
  --output ./data/graph_csv \
  --workers 16 \
  --gcs-bucket <YOUR_BUCKET> \
  --gcs-prefix demo-data \
  --gcs-delete-local
```

3. Build/upload artifacts to GCP bucket

- Latest Bulkloader JAR (`https://aerospike.com/download/graph/loader/`)
- Customize the config in **[this file](./../java-backend/src/main/resources/static/config_fraud.properties)**

```bash
gsutil cp bulk-load.jar gs://<YOUR_BUCKET>/artifacts/
gsutil cp java-backend/src/main/resources/static/config_fraud.properties gs://<YOUR_BUCKET>/config/
```

4. Sign into your GCloud Account
Using the bulkloader creates a dataproc cluster and job, which means that it needs elevated permissions.
```bash
gcloud auth login
```

## Configure bulkload script with your GCP data

Set the following variables in `java-backend/src/main/resources/distributed-bulkload.sh`:

```bash
dataproc_name="<Dataproc-cluster-name>"
region=us-central1
zone=us-central1-a
instance_type=n2d-highmem-8
num_workers=8
project=<Your-GCP-Project-Name>
bulk_jar_uri="gs://<Your-GCP-Bucket>/<path-to-bulkload-jar>"
properties_file_uri="gs://<Your-GCP-Bucket>/<path-to-properties-file>"
```

Then invoke the script to kick off bulk load.
This will create a dataproc cluster in your GCP project, alongside workers to efficiently load massive quantities
of data into AGS.
**NOTE** Make sure after loading has completed successfully to destroy the dataproc cluster to save resources.

---

# Testing / Running

If you want a quick way to test the backend quickly, start the CLI with

```bash
cd java-backend
mvn spring-boot:run -Dspring-boot.run.profiles=cli
```

_Useful commands_

- txns: returns stats on transactions
- start #: Starts generator at given amount
- stop: Stops the generator

If you want to test out the frontend as well, navigate to the frontend and run the dev:

```bash
cd ../frontend
npm run dev
```

If you would like to deploy this, refer to the [deployment docs file](./deployment.md)