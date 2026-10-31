"""Synthetic workload only; no research/model implementation."""
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import psycopg
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

SERVICE = os.environ.get('SERVICE_NAME', 'api')
REQUESTS = Counter('aim_http_requests', 'Completed application requests', ['service', 'route', 'status'])
RECEIVED = Counter('aim_http_received_requests', 'Chamadas recebidas pelo handler, excluindo health e metrics', ['service'])
ACTIVE = Gauge('aim_http_active_requests', 'Chamadas em processamento no handler HTTP', ['service'])
LATENCY = Histogram('aim_http_request_duration_seconds', 'Application request duration', ['service', 'route'])
DB = Counter('aim_db_operations', 'Successful database operations', ['service'])
RECEIVED.labels(SERVICE)
ACTIVE.labels(SERVICE)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = self.path.split('?')[0]
        if route == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
            return
        if route == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
            return
        RECEIVED.labels(SERVICE).inc()
        ACTIVE.labels(SERVICE).inc()
        try:
            self.application_request(route)
        finally:
            ACTIVE.labels(SERVICE).dec()

    def application_request(self, route):
        started = time.perf_counter()
        status, body = 404, b'not found'
        bounded_route = '/work' if route == '/work' else 'unknown'
        if route == '/work':
            try:
                with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=3) as conn:
                    conn.execute('INSERT INTO events(service) VALUES (%s)', (SERVICE,))
                DB.labels(SERVICE).inc()
                status, body = 200, b'{"ok":true}'
            except Exception:
                status, body = 503, b'{"ok":false}'
        REQUESTS.labels(SERVICE, bounded_route, str(status)).inc()
        LATENCY.labels(SERVICE, bounded_route).observe(time.perf_counter() - started)
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)

ThreadingHTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
