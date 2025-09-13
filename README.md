
**To Update/Deploy**

- Ensure Google cloud artifacte reigstry, cloud run, firebase database setup access added

run: gcloud auth login

- gcloud builds submit --tag gcr.io/xbot-2b603/extend-auth

gcloud run deploy extend-auth \
--image=gcr.io/xbot-2b603/extend-auth \
--platform=managed \
--region=us-central1 \
--allow-unauthenticated

- replace "xbot-2b603" with your cloud project id

- To see projects: gcloud projects list

- To switch projects: gcloud config set project xbot-2b603

- To see current project: gcloud config get-value project

https://extend-auth-247357760734.us-central1.run.app
