def stdout_handler(config):
    def handle(event):
        print(event._formatted)
    return handle
