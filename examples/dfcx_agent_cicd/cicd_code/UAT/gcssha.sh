
# Set your GCS bucket name and destination directory
apt-get update && apt-get install -y jq
export GCS_BUCKET=$(jq -r .bucket config.json)
export agent_name=$(jq -r .agent_name config.json)
export DESTINATION_DIR="UAT/${agent_name}/"
echo $DESTINATION_DIR
# Create a local directory
mkdir -p $1

# Copy your two files to the local directory
cp agent_artifacts/$agent_name $1
cp agent_artifacts/metadata.json $1

# Upload the local directory to GCS
gsutil -m cp -r $1 "gs://$GCS_BUCKET/$DESTINATION_DIR"

# Clean up the local directory if needed
rm -r $1

echo "Files copied and uploaded to GCS."