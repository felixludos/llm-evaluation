from typing import List, Dict, Any, Tuple, Union, Optional, Iterable, Iterator, Generator
from pathlib import Path
from omnibelt import load_json, save_json, load_csv, load_yaml, save_yaml, load_csv_rows
import omnifig as fig
from datetime import datetime

import time
import psutil
import torch
import humanize
from pynvml.smi import nvidia_smi
from dataclasses import dataclass
from contextlib import nullcontext
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
from transformers import pipeline
from transformers import LlamaTokenizer, LlamaForCausalLM, GenerationConfig, pipeline, BitsAndBytesConfig , CodeGenTokenizer
# from langchain.llms import HuggingFacePipeline
# from langchain import PromptTemplate, LLMChain
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
from transformers import AutoTokenizer , AutoModelForCausalLM

from transformers.utils.logging import disable_progress_bar

# from huggingface_hub import WebhooksServer, WebhookPayload










