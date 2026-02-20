from fastapi import FastAPI
import gradio as gr

app = FastAPI()

def predict(x):
	return x*2

gradio_app = gr.Interface(fn=predict, inputs="number", outputs="number")

@app.get('/')
def root():
	return {"message": "runs"}
