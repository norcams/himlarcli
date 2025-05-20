1. Generate access token for Nettskjema API v3 for skjema 289417

The access token is valid for 86400 seconds (24 hours),
or until this script is re-run:

```bash
source create-nettskjema-access-token.sh
```

Note! Your Nettskjema API client Username (e.g.: bb910dc1-1c15-458c-b5cd-de72890ca13a@apiclient)
needs to be added to https://nettskjema.no/user/form/289417/settings#permissions

2. Predict CLI from Nettskjema Ref. selected-to-latest

```bash
bash new-project.sh SUBMISSIN_ID
```
