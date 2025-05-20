1. Create Nettskjema API Client at ```https://authorization.nettskjema.no/client```

2. Copy Client Id and Client Secret and paste to clientId and clientSecret in ```create-nettskjema-access-token.sh```

3. Copy Nettskjema API Client Username (e.g.: bb910dc1-1c15-458c-b5cd-de72890ca13a@apiclient) from ```https://authorization.nettskjema.no/client``` and paste to ```https://nettskjema.no/user/form/289417/settings#permissions```

4. Generate access token for Nettskjema API v3 for skjema 289417

The access token is valid for 86400 seconds (24 hours),
or until this script is re-run:

```bash
source create-nettskjema-access-token.sh
```

5. Predict CLI from Nettskjema Ref. selected-to-latest

```bash
bash new-project.sh SUBMISSION_ID
```
