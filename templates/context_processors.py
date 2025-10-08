from tuktuk.settings import HOST, PORT


def websocket_url(request):
    return {"websocket_url": f"ws://{HOST}:{PORT}/", "http_url": f"http://{HOST}:{PORT}"}
