#!/bin/bash
: '
bash new-project.sh FROM_SUBMISSION_ID

Process oldest to newest (FIFO)

FROM_SUBMISSION_ID is included

bash new-project.sh --dumpjson|--dumphuman SUBMISSION_ID

Dump the answer data of one submission (raw JSON, or
human readable) and exit.

export NETTSKJEMA_API_ACCESS_TOKEN=TOKEN

API v3 Reference:

https://www.uio.no/tjenester/it/adm-app/nettskjema/hjelp/api-clients-v3.md
https://nettskjema.no/api/v3/swagger-ui/index.html#/
'

dumpMode=""
case "$1" in
  --dumpjson|--dumphuman)
    dumpMode="$1"
    shift
    ;;
esac

fromSubmissionId=$1

if [ -z $NETTSKJEMA_API_ACCESS_TOKEN ]
then
  echo 'NETSKJEMA_API_ACCESS_TOKEN environmental variable not present!'
  echo 'You need to source bin/predict/create-nettskjema-access-token.sh'
  echo 'exiting script'
  exit
fi

# element_data only needed for the human readable dump
element_data=""
if [[ -z $dumpMode || $dumpMode == "--dumphuman" ]]
then
  element_data=$(curl -s -H "Authorization: Bearer ${NETTSKJEMA_API_ACCESS_TOKEN}" -X GET https://nettskjema.no/api/v3/form/289417/elements)
fi

# Debug
#echo $element_data > element_data.json

if [ ! -z $dumpMode ]
then
  # fromSubmissionId here is the SUBMISSION_ID to dump
  bash $(dirname $0)/lib/new-project-submission-cmds.sh "" $fromSubmissionId "$element_data" $dumpMode
  exit
fi

submissionIds=($(bash $(dirname $0)/lib/new-project-submission-ids.sh $(($fromSubmissionId-1))))

numSubmissions=${#submissionIds[*]}

# FIFO
for ((i=$(($numSubmissions-1)); i>=0 ; --i))
do
  echo "New submission"
  submissionId=${submissionIds[$i]}
  read -p "#RT for Ref. $submissionId is (Enter to skip) " rt
  #echo "$rt $submissionId"
  if [ ! -z $rt ]
  then
    bash $(dirname $0)/lib/new-project-submission-cmds.sh $rt $submissionId "$element_data"
  fi
done
echo "Done"
