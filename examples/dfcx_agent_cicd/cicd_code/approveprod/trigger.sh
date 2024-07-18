curl --request POST \
    'https://cloudbuild.googleapis.com/v1/projects/devopsprojecthere/locations/us-central1/builds/appbuildhere:approve?access_token=tokenhere' \
    --header 'Accept: application/json'\
    --header 'Content-Type:application/json' --data \
    '{"approvalResult":{"decision":"APPROVED","comment":"commenthere","approverAccount":"approverhere"}}' \
    --compressed