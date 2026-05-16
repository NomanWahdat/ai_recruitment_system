class LLMService:
    def __init__(self, model_router=None):
        self.model_router = model_router

    def run(self, payload, provider_name=None):
        raise NotImplementedError
