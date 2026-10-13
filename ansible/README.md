# Smart Travel Buddy: OpenShift AI automation

These Ansible playbooks set up a freshly provisioned OpenShift cluster to run Smart Travel Buddy.
They install OpenShift GitOps, enable MLflow and TrustyAI, deploy the app, the Gemma 4 model
(from the OpenShift AI Model catalog) and NeMo Guardrails with Argo CD, and wire the app to the
model, MLflow and NeMo Guardrails.

Everything is applied as Kubernetes / OpenShift AI manifests through the `kubernetes.core`
collection, using your current `oc login` session.

## Assumptions about the cluster

- The cluster is fully functional and has a **single NVIDIA GPU**.
- The **OpenShift AI operator** is installed and the `default-dsc` DataScienceCluster is ready
  (KServe enabled).
- Infra dependencies (NVIDIA GPU operator, Node Feature Discovery, storage with a default
  StorageClass) are in place.

## Prerequisites

On the machine that runs the playbooks:

```bash
cd ansible
python3 -m pip install -r requirements.txt          # ansible-core + kubernetes Python client
ansible-galaxy collection install -r requirements.yml
oc login https://api.<cluster-domain>:6443 -u <cluster-admin-user>
```

The logged-in user must be a cluster admin.

### Where the model is defined

The Gemma 4 model is deployed by its own Argo CD application, `gemma-4-model`
([gitops/argocd/application-model.yaml](../gitops/argocd/application-model.yaml)), from the
manifests in [gitops/model/](../gitops/model/):

- `servingruntime.yaml`: vLLM runtime, copied from OpenShift AI's `vllm-cuda-runtime-template`.
- `inferenceservice.yaml`: the model (`oci://` model location from the Model catalog, 1 GPU,
  token auth).
- `auth.yaml`: the ServiceAccount, Role, RoleBinding and token Secret used to call the model.

To change the model, its resources or vLLM arguments, edit those files and push. Argo CD applies
the change. After an OpenShift AI upgrade, update the vLLM image digest in `servingruntime.yaml`:

```bash
oc get template vllm-cuda-runtime-template -n redhat-ods-applications \
  -o jsonpath='{.objects[0].spec.containers[0].image}'
```

### Where NeMo Guardrails is defined

NeMo Guardrails is deployed by its own Argo CD application, `guardrails`
([gitops/argocd/application-guardrails.yaml](../gitops/argocd/application-guardrails.yaml)), from
the manifests in [gitops/guardrails/](../gitops/guardrails/):

- `configmap.yaml`: the rails. Input: Presidio sensitive data (email, phone, credit card, SSN,
  IBAN), a regex for passwords/secrets/API keys, and an LLM self-check for jailbreaks and abusive
  content. Output: an LLM self-check of the itinerary. The self-checks use Gemma 4.
- `nemoguardrails.yaml`: the `NemoGuardrails` service `travel-guardrails` (token auth enabled).
- `backend-rolebinding.yaml`: gives the backend's service account `view` in the namespace, which
  NeMo Guardrails requires from its callers.

The backend only calls NeMo Guardrails when the **Guardrails** switch in the chat header is on.
With the switch off (the default), the workflow is unchanged.

## Usage

Run everything (you are prompted for the OpenWeatherMap API key at the start):

```bash
ansible-playbook site.yml
```

Pass the key on the command line instead of being prompted:

```bash
ansible-playbook site.yml -e openweathermap_api_key=XXXX
```

`site.yml` is the single entry point. It asks for the OpenWeatherMap key once, then runs
`playbooks/01` to `11` in order. Each playbook can also be run on its own, for example to repeat
one step:

```bash
ansible-playbook playbooks/04-ai-components.yml
ansible-playbook playbooks/07-app-config.yml -e openweathermap_api_key=XXXX
```

All playbooks are idempotent and safe to re-run. Run them from the `ansible/` directory so that
`ansible.cfg` and the inventory are picked up.

## What each playbook does

| Playbook | Step | What it creates / does |
|---|---|---|
| [01-prepare-gpu.yml](playbooks/01-prepare-gpu.yml) | 1 | Stops any other model running in the cluster (any `InferenceService` or `LLMInferenceService` in any namespace), the same as the dashboard's **Stop** action (`serving.kserve.io/stop: "true"`), and waits for its pods to go away so the single GPU is free. Creates the `smart-travel-buddy` namespace as a Data Science Project, and starts Gemma 4 again if it was stopped. |
| [02-gitops-operator.yml](playbooks/02-gitops-operator.yml) | 2 | Installs the **OpenShift GitOps** operator (Namespace, OperatorGroup, Subscription on channel `latest`). Waits for the CSV and the default `openshift-gitops` Argo CD instance. |
| [03-cluster-admins.yml](playbooks/03-cluster-admins.yml) | 3 | Creates the `cluster-admins` group with the `admin` user and binds it to the `cluster-admin` ClusterRole. OpenShift GitOps gives this group admin rights in Argo CD. |
| [04-ai-components.yml](playbooks/04-ai-components.yml) | 4 | Sets `mlflowoperator` and `trustyai` to `Managed` on `default-dsc` and waits for the MLflow and NeMo Guardrails CRDs. Then creates the `MLflow` instance in `redhat-ods-applications` (10Gi PVC, SQLite backend, local artifacts). |
| [05-model-deployment.yml](playbooks/05-model-deployment.yml) | 5 | Applies the `workloads` AppProject from [application-container.yaml](../gitops/argocd/application-container.yaml) and the `gemma-4-model` Argo CD application ([application-model.yaml](../gitops/argocd/application-model.yaml)). Waits for the model to be `Ready` and its API token to be issued. |
| [06-guardrails-deployment.yml](playbooks/06-guardrails-deployment.yml) | 6 | Applies the `guardrails` Argo CD application ([application-guardrails.yaml](../gitops/argocd/application-guardrails.yaml)) and waits for the `NemoGuardrails` resource. NeMo Guardrails needs the `api-keys` Secret to start, so step 7 waits for it to be available. |
| [07-app-config.yml](playbooks/07-app-config.yml) | 7 | Asks for the OpenWeatherMap API key (if not already given). Reads the Gemma 4 API token and internal endpoint from the cluster and creates the `api-keys` Secret. Waits for NeMo Guardrails, which needs that Secret, then creates the `backend-config` ConfigMap in `smart-travel-buddy`, including the NeMo Guardrails URL. |
| [08-build-images.yml](playbooks/08-build-images.yml) | 8 | Installs the **OpenShift Pipelines** operator (Subscription on channel `latest`) if needed, applies the `smart-travel-buddy-build` Pipeline from [tekton/](../tekton/) in the `smart-travel-buddy-pipeline` namespace, with RoleBindings that let it push images to and restart the deployments of `smart-travel-buddy`, and runs it. The Pipeline builds the five app images from Git (`pipeline_git_url` / `pipeline_git_revision`, not your local working tree) and pushes them to the internal registry of `smart-travel-buddy`. Waits for the PipelineRun to succeed, so the images exist before Argo CD deploys the app. |
| [09-argocd-app.yml](playbooks/09-argocd-app.yml) | 9 | Applies [application-container.yaml](../gitops/argocd/application-container.yaml) (the `workloads` AppProject + the `smart-travel-buddy` Argo CD application) and waits for the backend Deployment. The Secret, ConfigMap and images already exist, so the app pods start right away. |
| [10-restart-backend.yml](playbooks/10-restart-backend.yml) | 10 | Deletes the backend pod and waits for the new one to be ready, so it picks up the new Secret and ConfigMap. |
| [11-show-url.yml](playbooks/11-show-url.yml) | – | Prints `Smart Travel Buddy agent is available at https://<frontend route>`. |

### Values written to the app configuration

| Key | Source |
|---|---|
| `api-keys` / `llm-api-key` | Token from Secret `default-name-redhataigemma-4-12b-it-fp8-dyn-sa` |
| `api-keys` / `openweathermap` | OpenWeatherMap key you entered |
| `backend-config` / `llm-model` | `redhataigemma-4-12b-it-fp8-dyn` |
| `backend-config` / `llm-base-url` | InferenceService `status.address.url` (internal, cluster-local HTTPS) + `/v1` |
| `backend-config` / `mlflow-tracking-uri` | `https://rh-ai.<cluster apps domain>/mlflow/` |
| `backend-config` / `mlflow-experiment-name` | `smart-travel-buddy` |
| `backend-config` / `mlflow-tracking-auth` | `kubernetes-namespaced` |
| `backend-config` / `mlflow-workspace` | `smart-travel-buddy` |
| `backend-config` / `guardrails-url` | NeMo Guardrails internal service URL (`https://travel-guardrails.smart-travel-buddy.svc.cluster.local`) |

The Secret and ConfigMap are not stored in Git, so Argo CD does not manage or prune them.

## Variables

All variables live in [inventory/group_vars/all.yml](inventory/group_vars/all.yml). You can
override any of them with `-e name=value`.

| Variable | Default | Description |
|---|---|---|
| `openweathermap_api_key` | *(prompted)* | OpenWeatherMap API key. |
| `app_namespace` | `smart-travel-buddy` | Namespace of the app (and, by default, of the model). |
| `model_namespace` | `{{ app_namespace }}` | Data Science Project the model is deployed in. |
| `model_name` | `redhataigemma-4-12b-it-fp8-dyn` | InferenceService name (must match `gitops/model/`). Also the model name served by vLLM. |
| `model_ready_timeout` | `1800` | Seconds to wait for the model to become Ready. |
| `model_stop_timeout` | `600` | Seconds to wait for other running models to stop and release the GPU. |
| `guardrails_name` | `travel-guardrails` | `NemoGuardrails` name (must match `gitops/guardrails/`). |
| `guardrails_timeout` | `600` | Seconds to wait for NeMo Guardrails to be available. |
| `pipelines_channel` | `latest` | OpenShift Pipelines operator channel. |
| `pipeline_namespace` | `smart-travel-buddy-pipeline` | Namespace of the Pipeline and its PipelineRuns. |
| `pipeline_git_url` / `pipeline_git_revision` | this repo / `master` | Git repository and revision the images are built from. |
| `pipeline_timeout` | `1800` | Seconds to wait for the image build PipelineRun. |
| `gitops_channel` | `latest` | OpenShift GitOps operator channel. |
| `cluster_admin_group` / `cluster_admin_users` | `cluster-admins` / `[admin]` | Group and its members. |
| `dsc_name` | `default-dsc` | DataScienceCluster to patch. |
| `mlflow_namespace` | `redhat-ods-applications` | Namespace of the MLflow instance. |
| `mlflow_host_prefix` | `rh-ai` | Host prefix of the OpenShift AI gateway used in the MLflow URI. |
| `argocd_app_url` | GitHub raw URL of `application-container.yaml` | Argo CD AppProject + app. |
| `argocd_model_app_url` | GitHub raw URL of `application-model.yaml` | Argo CD application for the model. |
| `argocd_guardrails_app_url` | GitHub raw URL of `application-guardrails.yaml` | Argo CD application for NeMo Guardrails. |

## Verifying the deployment

```bash
oc get inferenceservice -n smart-travel-buddy                 # READY = True
oc get mlflow -n redhat-ods-applications
oc get nemoguardrails -n smart-travel-buddy                   # PHASE = Ready
oc get applications.argoproj.io -n openshift-gitops           # Synced / Healthy
oc get secret api-keys configmap backend-config -n smart-travel-buddy
oc get pods -n smart-travel-buddy

# Call the model through its internal endpoint from inside the cluster
TOKEN=$(oc get secret default-name-redhataigemma-4-12b-it-fp8-dyn-sa -n smart-travel-buddy -o jsonpath='{.data.token}' | base64 -d)
URL=$(oc get cm backend-config -n smart-travel-buddy -o jsonpath='{.data.llm-base-url}')
oc run model-check --rm -i --restart=Never -n smart-travel-buddy \
  --image=registry.access.redhat.com/ubi9/ubi-minimal -- \
  curl -sk -H "Authorization: Bearer $TOKEN" "$URL/models"

# Print the app URL again
ansible-playbook playbooks/11-show-url.yml
```

## Troubleshooting

- **Other models were stopped.** Step 1 stops every other running model, but it does not delete them. Start one again from the dashboard, or with
  `oc annotate inferenceservice <name> -n <namespace> serving.kserve.io/stop=false --overwrite`
  (only after stopping Gemma 4 the same way, since there is one GPU).
- **Image build fails (step 8).** Inspect the run with
  `tkn pipelinerun list -n smart-travel-buddy-pipeline` and `tkn pipelinerun logs <name> -n smart-travel-buddy-pipeline`,
  then re-run `ansible-playbook playbooks/08-build-images.yml` and continue with steps 9–10.
- **Model never becomes Ready.** Check the predictor pod with
  `oc get pods -n smart-travel-buddy -l serving.kserve.io/inferenceservice=redhataigemma-4-12b-it-fp8-dyn`
  and `oc logs`. Pulling the model image can take a long time on first run. If vLLM fails with a
  KV-cache / out-of-memory error, lower the context window by adding `args: ["--max-model-len=16384"]`
  under `spec.predictor.model` in `gitops/model/inferenceservice.yaml`. If the pod is `Pending`, check that the
  GPU is free and schedulable (`oc describe node <gpu-node> | grep nvidia.com/gpu`).
- **Model stopped from the dashboard.** Argo CD does not start it again (the manifests leave
  `serving.kserve.io/stop` unset). Start it from the dashboard or re-run `playbooks/01-prepare-gpu.yml`.
- **Argo CD app not syncing.** Check it with `oc get application smart-travel-buddy -n openshift-gitops -o yaml`
  (or `gemma-4-model` for the model, `guardrails` for NeMo Guardrails),
  or open the Argo CD UI (route `openshift-gitops-server` in `openshift-gitops`) and log in with
  OpenShift as a member of `cluster-admins`.
- **Guardrails switch is greyed out.** The backend has no `guardrails-url`. Check that
  `oc get cm backend-config -n smart-travel-buddy -o jsonpath='{.data.guardrails-url}'` is set,
  then re-run steps 7 and 10.
- **NeMo Guardrails pod not starting.** It needs the `api-keys` Secret (step 7). Check
  `oc describe pod -l app=travel-guardrails -n smart-travel-buddy` and
  `oc logs deploy/travel-guardrails -n smart-travel-buddy -c nemo-guardrails`.
- **MLflow not Ready.** Step 4 only warns and continues. Inspect it with
  `oc get mlflow mlflow -n redhat-ods-applications -o yaml` and the pods in `redhat-ods-applications`.
- **Backend cannot reach the model or MLflow.** Check the values with
  `oc get cm backend-config -n smart-travel-buddy -o yaml` and the backend logs with
  `oc logs deploy/backend -n smart-travel-buddy`. Re-run steps 7 and 10 after any fix:
  `ansible-playbook playbooks/07-app-config.yml playbooks/10-restart-backend.yml`.
