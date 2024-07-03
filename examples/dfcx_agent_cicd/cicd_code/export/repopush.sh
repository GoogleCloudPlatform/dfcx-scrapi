apt-get update && apt-get install -y jq
export project_id=$(jq -r .devops_project config.json)
export agent_name=$(jq -r .agent_name config.json)
echo $agent_name
cd agenttemp
ls -all
gcloud source repos clone agentcicd --project=$project_id
#git remote add google 'https://source.developers.google.com/p/vs-kit-387413/r/agentTest'

cd agentcicd
git checkout main
ls -all

rm agent_artifacts/*
cp ../$agent_name agent_artifacts/
cp ../metadata.json agent_artifacts/
date > agent_artifacts/timestamp.txt
cd agent_artifacts
ls
cd ..
echo $3
git config --global user.name $2
git config --global user.email $3

git add .
echo "$1"
git diff --name-only
git commit --allow-empty -m "$1"

git push -u origin main