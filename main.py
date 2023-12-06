import asyncio
import os
from typing import Union

import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Инициализация приложения FastAPI
app = FastAPI()

# Загрузка ключа API OpenAI из переменных окружения
openai_api_key = "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"
openai.api_key = openai_api_key

# Модель Pydantic для данных запроса на суммаризацию
class SummarizeRequest(BaseModel):
    message: str

# Модель Pydantic для данных запроса на чат
class ChatRequest(BaseModel):
    message: str
    thread_id: Union[str, None] = None

# Функция для выполнения суммаризации (асинхронная)
async def perform_summarization(message: str):
    print("Starting summarisation process...")
    
    client = openai.Client()
    assistant_id = "asst_CjvyFIeraCLKB8NTAqF0FhqG"

    # Run blocking operations in a background thread
    thread = await asyncio.to_thread(client.beta.threads.create)
    print(f"Thread created with ID: {thread.id}")

    await asyncio.to_thread(client.beta.threads.messages.create, thread_id=thread.id, role="user", content=message)
    print("Message added to the thread.")

    run = await asyncio.to_thread(client.beta.threads.runs.create, thread_id=thread.id, assistant_id="asst_kCSrKaHjh589gbKr2fphQ93T")
    print(f"Run started with ID: {run.id}")

    async def check_run_status(thread_id, run_id):
        try:
            run = await asyncio.to_thread(client.beta.threads.runs.retrieve, thread_id=thread_id, run_id=run_id)
            print(f"Run status: {run.status}")
            return run.status
        except Exception as e:
            print(f"Error retrieving run status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    start_time = asyncio.get_event_loop().time()
    while True:
        if asyncio.get_event_loop().time() - start_time > 7:
            print("Run did not complete in time.")
            raise HTTPException(status_code=500, detail="Run did not complete in time.")
        
        status = await check_run_status(thread.id, run.id)
        if status == 'completed':
            print("Run completed successfully.")
            break
        elif status in ['failed', 'cancelled']:
            print(f"Run {status}.")
            raise HTTPException(status_code=500, detail=f"Run {status}")
        await asyncio.sleep(0.5)

    messages = await asyncio.to_thread(client.beta.threads.messages.list, thread_id=thread.id)
    
    for message in messages.data:
        if message.role == "assistant" and message.content:
            text_content = message.content[0].text
            if text_content:
                print("Returning the assistant's response.")
                return {"assistant_response": text_content.value}

    print("No response from the assistant.")
    raise HTTPException(status_code=500, detail="No response from the assistant")


# Функция для отправки сообщения и получения ответа в чате (асинхронная)
async def send_message_get_reply(message: str, thread_id: Union[str, None]):
    client = openai.Client(api_key=openai_api_key)
    assistant_id = "asst_CjvyFIeraCLKB8NTAqF0FhqG"  # ID вашего помощника

    if thread_id is None:
        thread = await asyncio.to_thread(client.beta.threads.create)
        thread_id = thread.id

    await asyncio.to_thread(client.beta.threads.messages.create, thread_id=thread_id, role="user", content=message)
    run = await asyncio.to_thread(client.beta.threads.runs.create, thread_id=thread_id, assistant_id=assistant_id)

    while True:
        run_status = await asyncio.to_thread(client.beta.threads.runs.retrieve, thread_id=thread_id, run_id=run.id)
        if run_status.status == 'completed':
            break
        elif run_status.status in ['failed', 'cancelled']:
            return None, thread_id
        await asyncio.sleep(0.5)

    messages = await asyncio.to_thread(client.beta.threads.messages.list, thread_id=thread_id)
    last_message = next((m.content[0].text.value for m in messages.data if m.role == "assistant" and m.content), None)
    return last_message, thread_id

# Конечная точка для проверки работоспособности
@app.get("/")
async def root():
    return {"message": "Да вроди работает"}

# Конечная точка для суммаризации
@app.post("/summarize/")
async def summarize(request: SummarizeRequest):
    summarized_text = await perform_summarization(request.message)
    return {"summarized_text": summarized_text}

# Конечная точка для чата
@app.post("/chat/")
async def chat(request: ChatRequest):
    response, thread_id = await send_message_get_reply(request.message, request.thread_id)
    if response is None:
        raise HTTPException(status_code=500, detail="Не удалось получить ответ от помощника")
    return {"response": response, "thread_id": thread_id}

# Запуск приложения FastAPI с Uvicorn
# Обычно эту команду вызывают из командной строки
# uvicorn.run(app, host="0.0.0.0", port=8000)
