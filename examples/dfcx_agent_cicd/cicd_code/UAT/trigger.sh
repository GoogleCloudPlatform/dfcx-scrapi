echo $1
apt-get update && apt-get install -y jq
export devops_project_id=$(jq -r .devops_project config.json)
export prod_project_id=$(jq -r .prod_project config.json)

#Use below command to trigger the build if manual invokation is used. Since there is no secret , no extra charges

export build_info=$(gcloud builds triggers run prodbuild --project=$devops_project_id --substitutions=_COMMIT_SHA=$1 --region=us-central1 --format=json)
echo "devops prod triggerdone"


#getting the trigger id of the above trigger

export prod_build_id=$(echo "$build_info" | jq -r '.metadata.build.id')
echo "build id returned back is"
echo $prod_build_id


#Trigger the build in prod project which is used for approval
gcloud builds triggers run prodapprovebuild --project=$devops_project_id --substitutions=_APP_BUILD_ID=$prod_build_id --region=us-central1

echo "prod project approve build triggered"