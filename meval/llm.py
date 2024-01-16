from .imports import *


@fig.script('llm')
def start_llm(cfg: fig.Configuration):
    # 2. Create WebhooksServer with custom UI and secret
    app = WebhooksServer(webhook_secret="my_secret_key")

    # 3. Register webhook with explicit name
    @app.add_webhook("/say_hello")
    async def hello(payload: WebhookPayload):
        return {"message": "hello"}

    # 4. Register webhook with implicit name
    @app.add_webhook
    async def goodbye(payload: WebhookPayload):
        return {"message": "goodbye"}

    cfg.print('Starting server')

    app.run()














