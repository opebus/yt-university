from modal import Dict, Image, Secret, Stub, asgi_app

stub = Stub("yt-university")

in_progress = Dict.from_name("transcriber-in-progress", create_if_missing=True)

shared_webapp_image = (
    Image.debian_slim(python_version="3.11")
    .apt_install("libpq-dev")
    .pip_install("python-dotenv", "psycopg2", "asyncpg", "sqlalchemy", "supabase")
)


@stub.function(image=shared_webapp_image, secrets=[Secret.from_name("supabase")])
@asgi_app()
def app():
    from yt_university.api.app import web_app

    return web_app
