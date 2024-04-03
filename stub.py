from modal import Stub, asgi_app

stub = Stub("yt-university")

@stub.function(allow_concurrent_inputs=4)
@asgi_app()
def app():
    from yt_university.api.app import web_app

    return web_app
