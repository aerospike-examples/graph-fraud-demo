# Local Setup for Development and Testing

If you want to get on the ground running, this doc will have the app started in 5 easy steps.

Requires:

- npm
- node.js
- java 21
- maven
- docker
- gcloud
- GCP Authorized Service Worker Keyfile

1. Create a GCP Bucket
```bash
gsutil mb gs://BUCKET_NAME
```
2. Generate Data Into the Bucket

```bash
  python -m venv venv 
  .\venv\Scripts\activate
  pip install -r ./scripts/requirements.txt
```

This script will not only generate the data neccessary for this demo, but also load it into your GCP Bucket.

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

3. Start Aerospike Graph Service and Aerospike DB
Now put your GCP KeyFile under the directory `./secrets`, it will be mounted to the docker container for bulk loading.
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

4. Start the Backend

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

Now Seed the backend with the `seed` command in the CLI, and wait for it to finish.

5. Start the Frontend

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