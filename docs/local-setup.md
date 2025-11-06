# Local Setup for Development and Testing

If you want to get on the ground running, this doc will have the app started in 4 easy steps.

Requires:

- npm
- node.js
- java 21
- maven
- docker
- gcloud
- GCP Authorized Service Worker Keyfile

## 1. Start a Python Venv

Make a python venv and install the requirements
```bash
  python -m venv venv 
  .\venv\Scripts\activate
  pip install -r ./scripts/requirements.txt
```

## 2. Load Data
For loading the data you have two options:

a) Load from a GCP bucket

b) Load from locally mounted data in the docker container

### a) Load from locally mounted data in the docker container

Generate the data into the local folder
```bash
python3 ./scripts/generate_user_data_gcp.py \
  --users 20000 --region american \
  --output ./data/graph_csv \
  --workers 16 
```

Now when you compose the docker containers, it will mount to the AGS container.
Skip to part 3.

### b) Load from a GCP bucket
Create a GCP Bucket
```bash
gsutil mb gs://BUCKET_NAME
```

This script will generate the data needed and transfer it into your GCP bucket.
If you want to keep it locally as well, remove the `--gcs-delete-local` from the command:

**NOTE** Your current user must be authorized to place files in the GCP bucket
```bash
python3 ./scripts/generate_user_data_gcp.py \
  --users 20000 --region american \
  --output ./data/graph_csv \
  --workers 16 \
  --gcs-bucket BUCKET_NAME \
  --gcs-prefix demo-data \
  --gcs-delete-local
```

## 3. Start Aerospike Graph Service and Aerospike DB
If you chose the local bulk loading, skip to the docker compose command, if you chose GCP continue here.
Now put your GCP KeyFile under the directory `./secrets`, 
it will be mounted to the docker container for bulk loading.
Make sure the service account you are using has read/write permissions for your bucket.
If your not sure how to get a GCP Key, check out **[this guide.](https://cloud.google.com/iam/docs/keys-list-get)**
To make sure it can read them, use this command:
```bash
gsutil iam ch serviceAccount:<SA>@<PROJECT>.iam.gserviceaccount.com:objectViewer gs://<YOUR_BUCKET>
```


Now start the Aerospike Graph Service and DB
```bash
docker compose up -d 
```

## 3. Start the Backend

Go into the java backend, and in `java-backend/src/main/resources/application.properties` adjust the 
config to your liking.

Make sure to update the `graph.vertices-path` and `graph.edges-path` variables to your gcp path. For example,
```
graph.vertices-path=gs://BUCKET_NAME/demo-data/vertices
graph.edges-path=gs://BUCKET_NAME/demo-data/edges
```

Now that its configured, start your backend in CLI mode.
```
cd java-backend
mvn spring-boot:run -Dspring-boot.run.profiles=cli
```

Now if you chose GCP, use `seed gcp` command in the CLI, and wait for it to finish.
If you chose local, use `seed local` command in the CLI, and wait for it to finish.

## 4. Start the Frontend

```
cd frontend
npm run dev
```

or prod like:

```
cd frontend
npm run prod
```

That's it!
Navigate to the address outputted in the frontend startup, and your app will be ready!