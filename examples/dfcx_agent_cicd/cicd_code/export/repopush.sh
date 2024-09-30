apt-get update && apt-get install -y jq
export project_id=$(jq -r .devops_project config.json)
export agent_name=$(jq -r .agent_name config.json)
echo $agent_name
 
cd $1
git checkout main
echo "pwd"
pwd
date > agent_artifacts/timestamp.txt
rm agent_artifacts/*
cp /workspace/$2/agenttemp/$agent_name agent_artifacts/
cp /workspace/$2/agenttemp/metadata.json agent_artifacts/
date > agent_artifacts/timestamp.txt