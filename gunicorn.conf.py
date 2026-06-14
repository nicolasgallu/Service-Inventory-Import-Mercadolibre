import os

bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
workers = 1
threads = 2
worker_class = "sync"
timeout = 300
accesslog = "-"
errorlog = "-"