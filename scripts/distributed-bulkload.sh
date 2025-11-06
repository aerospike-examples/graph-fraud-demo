#!/bin/bash

# Edit all these variable to match your GCP environment.
# Ensure that the bulk-loader.jar file is correctly named
dataproc_name="<Dataproc-cluster-name>"
region=us-central1
zone=us-central1-a
instance_type=n2d-highmem-8
num_workers=8
project=<Your-GCP-Project-Name>
bulk_jar_uri="gs://<Your-GCP-Bucket>/<path-to-bulkload-jar>"
properties_file_uri="gs://<Your-GCP-Bucket>/<path-to-properties-file>"



# Execute the dataproc command
gcloud dataproc clusters create "$dataproc_name" \
    --enable-component-gateway \
    --region $region \
    --zone $zone \
    --master-machine-type "$instance_type" \
    --master-boot-disk-type pd-ssd \
    --master-boot-disk-size 35 \
    --num-workers "$num_workers" \
    --worker-machine-type "$instance_type" \
    --worker-boot-disk-type pd-ssd \
    --worker-boot-disk-size 35 \
    --image-version 2.1-debian11 \
    --properties spark:spark.history.fs.gs.outputstream.type=FLUSHABLE_COMPOSITE \
    --project $project

gcloud dataproc jobs submit spark \
    --class=com.aerospike.firefly.bulkloader.SparkBulkLoader \
    --jars="$bulk_jar_uri" \
    --cluster="$dataproc_name" \
    --region="$region" \
    -- -c "$properties_file_uri"