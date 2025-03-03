from .imports import *

from omnibelt import colorize

from .models import HuggingFaceModel
from .models import *


def test_create_context():
	# fig.initialize()
	# cfg = fig.create_config('debug')
	# worker = cfg.pull('worker')

	worker = Phi3(generate_args={'max_new_tokens': 200, 'max_time': 30})

	print()
	print(worker)

	worker.stage()

	ctx = Context(worker)
	ctx['prompt'] = 'Question: What is the capital of France?\nAnswer:'
# 	ctx['prompt'] = '''<|system|>
# You are a helpful AI assistant.<|end|>
# <|user|>
# Can you solve the equation 2x + 3 = 7?<|end|>
# <|assistant|>
# '''

	print()
	print(colorize(ctx['prompt'], 'cyan') + ctx['response'])

	print()
	print(ctx['inp_tok'], ctx['out_tok'])
	print()


	pass

import time
import humanize

@fig.script('test-chat')
def test_chat(cfg = None):

	worker = Phi3(generate_args={'max_new_tokens': 200, 'max_time': 30})

	tick = time.time()
	worker.stage()
	print(colorize(f'Model loaded in {humanize.naturaldelta(time.time() - tick)}', 'green'))

	ctx = Context(worker, ChatFormatting())
	# ctx['user'] = 'What is the capital of France?'
	ctx['user'] = 'Can you solve the equation 2x + 3 = 7?'

	print()

	tick = time.time()
	print(colorize(ctx['prompt'], 'cyan') + ctx['response'])
	dt = time.time() - tick
	print()
	print(colorize(f'Generating {ctx["out_tok"]} tokens (given {ctx["inp_tok"]}) took {humanize.naturaldelta(dt)} '
		  f'({ctx["out_tok"]/dt:.2f} tokens/sec)', 'green'))

	print()

	chat = ctx['chat_out']
	ctx.clear_cache()
	ctx['chat_in'] = chat
	ctx['user'] = 'Express your final answer as a number only. Say nothing else. Final answer:'

	print()

	tick = time.time()
	print(colorize(ctx['prompt'], 'cyan') + ctx['response'])
	dt = time.time() - tick
	print()
	print(colorize(f'Generating {ctx["out_tok"]} tokens (given {ctx["inp_tok"]}) took {humanize.naturaldelta(dt)} '
		  f'({ctx["out_tok"]/dt:.2f} tokens/sec)', 'green'))

	print()









