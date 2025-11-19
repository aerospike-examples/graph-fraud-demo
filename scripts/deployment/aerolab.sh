set -e #force script to fail if any step fails
source ./set_variables.sh

aerolab cluster create \
    --name "$name" \
    --count "$aerospike_count" \
    --instance "$aerospike_instance" \
    --aerospike-version "$aerospike_version" \
    --featurefile "$features_file" \
    --disk pd-ssd:20 \
    --disk local-ssd@"$aerospike_ssd_count" \
    --start n

aerolab cluster partition create \
      --name "$name" \
      --filter-type nvme \
      --partitions 24,24,24,24
aerolab cluster partition conf \
      --name "$name" \
      --namespace test \
      --filter-type nvme \
      --filter-partitions 1,2,3,4 \
      --configure device

aerolab aerospike start --name="$name"