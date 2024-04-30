import gradio as gr
# from huggingface_hub import InferenceClient

client = InferenceClient(model="http://127.0.0.1:8080")

def inference(message, history):
	partial_message = ""
	for token in client.text_generation(message, max_new_tokens=20, stream=True):
		partial_message += token
		yield partial_message

if __name__ == "__main__":
	gr.ChatInterface(
		inference,
		chatbot=gr.Chatbot(height=300),
		textbox=gr.Textbox(placeholder="Chat with me!", container=False, scale=7),
		description="This is the demo for Gradio UI consuming TGI endpoint with LLaMA 7B-Chat model.",
		title="Gradio 🤝 TGI",
		examples=["Are tomatoes vegetables?"],
		retry_btn="Retry",
		undo_btn="Undo",
		clear_btn="Clear",
	).queue().launch()