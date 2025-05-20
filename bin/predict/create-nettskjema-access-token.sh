: '
Generate access token for Nettskjema API v3

The access token is valid for 86400 seconds (24 hours),
or until this script is re-run:

source create-nettskjema-access-token.sh

The scripts need the following information from 
https://authorization.nettskjema.no/client
to create the access token (paste below):
'

clientId=''
clientSecret=''

NETTSKJEMA_API_ACCESS_TOKEN=$(curl -s -X POST -u "$clientId:$clientSecret" -d 'grant_type=client_credentials' https://authorization.nettskjema.no/oauth2/token | jq '.access_token' | tr -d '"')

export NETTSKJEMA_API_ACCESS_TOKEN=$NETTSKJEMA_API_ACCESS_TOKEN

