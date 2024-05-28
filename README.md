# llm-evaluation
Various methods to evaluate and interface with large language models.


This repo contains some scripts to help evaluate LLMs with a particular focus on inference (rather than training/fine-tuning). Currently, the repo is primarily designed to use Huggingface's [text-generation-inference](https://huggingface.co/docs/text-generation-inference/index) framework.

## Setup

For this section, it is not necessary to use this repo directly.

### Manually Loading Models

As a preliminary step, you can manually load the models (which requires some additional dependencies like `torch` and `transformers`). See this [notebook](./notebooks/model-loading.ipynb) for an example.

It is recommended that you download the model weights before launching the server which can be done using that notebook (with `device='cpu'` for models that exceed local resources). However, when running the server *locally* the models will be downloaded automatically. Note the default location for the models is `~/.cache/huggingface/hub/`.


### text-generation-inference

Serves models for inference through an HTTP server run using Rust. While the actually model inference is implemented in python, the server itself is implemented in Rust, making modifications rather involved. For the time being, you shouldn't need to make any changes to the server itself, however there are some steps necessary to run the server locally or on the (MPI) cluster.

#### Running Models Locally

Follow the installation instructions on the [text-generation-inference](https://huggingface.co/docs/text-generation-inference/installation) page. Once everything is installed you should be able to launch a server with Gemma 2b using this command:

```bash
text-generation-launcher --model-id google/gemma-2b-it --port 3000
```

Which should make the model available at `http://127.0.0.1:3000`.

If you don't have enough cuda memory, try running the (default) [bloom-560m](https://huggingface.co/bigscience/bloom-560m) model instead:

```bash
text-generation-launcher --port 3000
```

For more options see [documentation](https://huggingface.co/docs/text-generation-inference/basic_tutorials/launcher).

#### On the Cluster

To run the server on the cluster, you'll need to use the singularity container, however huggingface only provides a docker image. To convert the docker image to a singularity image, you can use the following command (recommended from an interactive node on the cluster):

```bash
singularity build text-generation-inference-2_0.sif docker://ghcr.io/huggingface/text-generation-inference:2.0
```

Then you can run the server using the following command:

```bash
singularity run --nv --bind ~/.cache/huggingface/hub/:/data text-generation-inference-2_0.sif --port 3000 --num-shard 2 --model-id meta-llama/Meta-Llama-3-70B-Instruct
```

Important note: the model must be fully downloaded before running the server *on the cluster* because of file write permission issues on the cluster prevents models from being downloaded automatically (see [internal wiki](https://atlas.is.localnet/confluence/display/IT/Using+huggingface+transformers+or+datasets)).

## Server Endpoints

Once the server is running there are several endpoints available, access `{URL}/docs` (e.g. `http://127.0.0.1:3000/docs`) for a full list of available endpoints and their parameters.

Also, there are some examples of how to use the server in this jupyter [notebook](./notebooks/tgi-endpoints.ipynb).


## QoL Wrappers

This repo provides some wrappers to simplify the launching and monitoring of servers. Documentation for that is coming soon.

To use these wrappers: Clone the repo and install dependencies in `requirements.txt`
- note that there are a few dependencies that are somewhat volatile (as I'm maintaining/extending them in parallel) so for `omnibelt`, `omnifig`, and `omniply` keep a close eye on the versions, and generally make sure you have the latest versions of those packages installed.


### Launching the Server

Locally:

```bash
fig serve local m/gemma
```

On the cluster (requires [`mpi_cluster` package](https://github.com/felixludos/mpi-cluster)):

```bash
fig submit-llm m/gemma --bid 100
```


### Chat Interface

Launch the Gradio chat interface offered by Huggingface locally (see [documentation](https://huggingface.co/docs/text-generation-inference/basic_tutorials/consuming_tgi#:~:text=for%20it%20here-,ChatUI,-ChatUI%20is%20an)) 

```bash
fig chat --url http://localnet:3000
```

### Benchmark Evaluation

[coming soon]



