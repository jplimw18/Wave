"""Executar no pod api-a: carga controlada e snapshots reais, sem calcular P/Q/S."""
import concurrent.futures
import datetime
import json
import re
import time
import urllib.error
import urllib.request

SERVICES = ('api-a', 'api-b')
RATES = (2, 8, 16, 25, 35, 35, 25, 16, 8, 2)
ERROR_FRACTIONS = (0, 0, 0, .1, .2, 0, 0, .1, 0, 0)
SECONDS = 5


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def snapshot(service):
    start = utc()
    status, raw = fetch('http://'+service+':8000/metrics')
    if status != 200:
        raise RuntimeError('Scrape falhou: '+service)
    def total(name):
        values = [float(line.split()[-1]) for line in raw.splitlines()
                  if re.match(r'^'+re.escape(name)+r'(?:\{|\s)', line)]
        return sum(values) if values else None
    failures = [float(line.split()[-1]) for line in raw.splitlines()
                if line.startswith('aim_http_requests_total{') and 'status="200"' not in line]
    return dict(start_utc=start, end_utc=utc(), monotonic_seconds=time.perf_counter(),
                cpu_seconds=total('process_cpu_seconds_total'),
                rss_bytes=total('process_resident_memory_bytes'),
                requests=total('aim_http_requests_total'),
                errors=sum(failures) if failures else None,
                latency_sum=total('aim_http_request_duration_seconds_sum'),
                latency_count=total('aim_http_request_duration_seconds_count'),
                prometheus=raw)


def measure(service, window, rate, fraction):
    before = snapshot(service)
    begin=time.perf_counter(); deadline=begin+SECONDS
    attempted=0; statuses={}; transport_failures=0
    # Marcador determinístico: todo décimo/quinto pedido usa rota inexistente.
    every = None if fraction == 0 else round(1/fraction)
    if rate == 0:
        time.sleep(SECONDS)
    while rate > 0 and time.perf_counter() < deadline:
        scheduled=begin+attempted/rate
        delay=scheduled-time.perf_counter()
        if delay>0:
            time.sleep(min(delay,max(0,deadline-time.perf_counter())))
        if time.perf_counter() >= deadline:
            break
        route='/synthetic-failure' if every and (attempted+1)%every==0 else '/work'
        attempted+=1
        try:
            status,_=fetch('http://'+service+':8000'+route)
            statuses[str(status)]=statuses.get(str(status),0)+1
        except (OSError, TimeoutError):
            transport_failures+=1
    after=snapshot(service)
    dt=after['monotonic_seconds']-before['monotonic_seconds']
    names=('requests','errors','latency_sum','latency_count','cpu_seconds')
    delta={key: None if before[key] is None or after[key] is None else after[key]-before[key]
           for key in names}
    reset=any(value is not None and value<0 for value in delta.values())
    count=delta['latency_count']
    return dict(service=service,window=window,source_kind='real_kubernetes_synthetic_workload',
                start_utc=before['end_utc'],end_utc=after['end_utc'],duration_seconds=dt,
                completed=None if delta['requests'] is None else round(delta['requests']),
                failed=None if delta['errors'] is None else round(delta['errors']),
                mean_latency_seconds=delta['latency_sum']/count if count and not reset else None,
                cpu_cores=delta['cpu_seconds']/dt if delta['cpu_seconds'] is not None and not reset else None,
                rss_bytes=after['rss_bytes'], counter_reset=reset,
                load=dict(target_rate=rate,nominal_seconds=SECONDS,injected_404_fraction=fraction,
                          attempted=attempted,statuses=statuses,transport_failures=transport_failures),
                before=before,after=after)


def main():
    started=utc()
    # Inicializa as séries 200/404 antes das janelas; health/metrics não são instrumentadas.
    for service in SERVICES:
        for route in ('/work','/synthetic-failure'):
            fetch('http://'+service+':8000'+route)
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for window,(rate,fraction) in enumerate(zip(RATES,ERROR_FRACTIONS)):
            futures=[pool.submit(measure,service,window,rate,fraction) for service in SERVICES]
            rows.extend(future.result() for future in futures)
    status,collector=fetch('http://otel-collector:8889/metrics')
    if status != 200:
        raise RuntimeError('Snapshot Collector indisponível')
    print(json.dumps(dict(capture_version='hypotenuse-capture-v1',start_utc=started,end_utc=utc(),
        source_kind='real_kubernetes_synthetic_workload',window_count_per_service=len(RATES),
        rates=RATES,error_fractions=ERROR_FRACTIONS,rows=rows,collector_prometheus=collector,
        notes=['Carga grava eventos sintéticos no PostgreSQL; preserva dados existentes.',
               '404 deliberado não simula falha interna de produção.',
               'CPU/RSS de processo não equivalem a consumo total de pod.',
               'Sem nova coleta kubeletstats ou mensuração de banda.',
               'Taxa alvo é ritmo de cliente serial, não benchmark de capacidade.',
               'Scrapes diretos das APIs; snapshot Collector confirma fluxo separado.']),indent=2))


if __name__=='__main__': main()
