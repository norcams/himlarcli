: '
bash new-project.sh FROM_SUBMISSION_ID

Process oldest to newest (FIFO)

FROM_SUBMISSION_ID is included

export NETTSKJEMA_API_ACCESS_TOKEN=TOKEN

API v3 Reference:

https://www.uio.no/tjenester/it/adm-app/nettskjema/hjelp/api-clients-v3.md
https://api.nettskjema.no/v3/swagger-ui/index.html#/
'

fromSubmissionId=$1

if [ -z $NETTSKJEMA_API_ACCESS_TOKEN ]
then
  echo 'NETSKJEMA_API_ACCESS_TOKEN environmental variable not present!'
  echo 'You need to source create-access-token.sh'
  echo 'exiting script'
  exit
fi

element_data=$(curl -s -H "Authorization: Bearer ${NETTSKJEMA_API_ACCESS_TOKEN}" -X GET https://api.nettskjema.no/v3/form/289417/elements)

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
