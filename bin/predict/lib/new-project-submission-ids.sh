: '
bash iaas-project-submission-ids.sh FROM_SUBMISSION_ID

FROM_SUBMISSION_ID not included

export NETTSKJEMA_API_API_TOKEN=TOKEN
'

FROM_SUBMISSION_ID=$1

curl -s -H "Authorization: Bearer ${NETTSKJEMA_API_ACCESS_TOKEN}" -X GET https://api.nettskjema.no/v3/form/289417/submission-metadata | jq "select(.submissionId>${FROM_SUBMISSION_ID}).submissionId" | sort -V -r

