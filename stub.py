from modal import Stub, asgi_app, Image, Secret

stub = Stub("yt-university")

webapp_image = (
    Image.debian_slim(python_version="3.11")
    .apt_install("libpq-dev")
    .pip_install("python-dotenv", "psycopg2", "asyncpg", "sqlalchemy", "supabase")
)


@stub.function(
    image=webapp_image,
    allow_concurrent_inputs=4,
    secrets=[Secret.from_name("supabase")],
)
@asgi_app()
def app():
    from yt_university.api.app import web_app

    return web_app
