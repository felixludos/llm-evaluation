
# Guide to Setup and Usage


## Setup

Some setup is required on the cluster and locally:

- Cluster: install dependencies (including `mpi_cluster`) to submit jobs to start the TGI server and monitor jobs. Also, you can submit longer client jobs to interface with any live servers.
- Locally: interface with the server, either manually by sending requests, through the chat interface, or using the provided endpoints.

For the installation of dependencies, see the [readme](./README.md).



## Downloading Models

Unfortunately, due to file write permission issues on the cluster, models must be fully downloaded before running the server on the cluster. This is because the server will attempt to download the model if it is not found locally, and this will fail due to the file write permissions.

To download a model, you can use the following command:

```bash
huggingface-cli download {model_id} --cache-dir {path_to_hf_hub_cache} --exclude {regex_pattern}
```

For example,

```bash
huggingface-cli download meta-llama/Meta-Llama-3-8B-Instruct --cache-dir /is/cluster/fast/fleeb/huggingface_cache/hub/ --exclude original*
```

Note that for some models (such as Llama 3), you have to first request access on the Huggingface website, and then make sure you are logged in to Huggingface using the command: `huggingface-cli login`.

## Launching Servers (on the cluster)

Next, to confirm that you can start the server, submit a job to the cluster for an interactive node.

```bash
condor_submit_bid 100 -i -append 'request_memory=81920' -append 'request_cpus=10' -append 'request_disk=100G' -append 'request_gpus=1'
```

### Running the Server through Singularity

Once you have the singularity container built (see readme), you can run the server using the following command:

```bash
singularity run --nv --bind {path_to_hf_hub_cache}:/data --bind {path_to_hf_home}:/cache --env HF_HOME=/cache{singularity_container_file} --port 3000 --model-id {model_id}
```

For example,

```bash
singularity run --nv --bind ~/.cache/huggingface/hub/:/data --bind ~/.cache/huggingface/:/cache --env HF_HOME=/cache text-generation-inference-2_0.sif --port 3000 --model-id meta-llama/Meta-Llama-3-8B-Instruct
```

If that starts the webserver successfully (you should see a message like "Connected"), then you can confirm that the server is running using port forwarding:

```bash
ssh -N -L {remote_port}:localhost:{local_port} {username}@login.cluster.is.localnet
```

For example,

```bash
ssh -N -L 3000:localhost:3000 fleeb@login.cluster.is.localnet
```

Then you can access the server at `http://localhost:3000/docs` to see the available endpoints.

### Launching the Server with `submit-llm`

There is a script that simplifies the process of submitting a job to the cluster to start the server. This script is called `submit-llm` (e.g. `fig -h submit-llm` may contain helpful information).

To use this script, you can run the following command:

```bash
fig submit-llm m/mistral --bid 100
```

The status of the server should be viewable at `local_tasks/log.jsonl`, or it can be customized by setting the `TASK_ROOT` environment variable to replace `local_tasks` with a different directory.


## Interfacing with the Server

Once the server is running, you can interface with it in



## Mock Server

Use [prism](https://github.com/stoplightio/prism) (can be installed through `npm`) to start a mock version of the TGI server. This can be useful for testing the client without needing to load/run a model.

```bash
prism mock assets/api-fixed.json
```
