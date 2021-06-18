def stdout_handler(config):
    def handle(event):
        print('>', event._formatted)
        print(event.message.strip())
    return handle
