"""Coleta nova: entradas e chamadas ativas, incluindo janelas sem carga."""
import concurrent.futures
import importlib.util
import json
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location('capture_base', Path(__file__).with_name('capture-hypotenuse.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
original_snapshot = base.snapshot
RATES = (0, 2, 8, 16, 25, 35, 35, 8, 2, 0)
ERROR_FRACTIONS = (0, 0, 0, 0, .1, .2, 0, .1, 0, 0)


def snapshot(service):
    raw = original_snapshot(service)
    def metric(name):
        values = [float(line.split()[-1]) for line in raw['prometheus'].splitlines()
                  if re.match(r'^'+re.escape(name)+r'(?:\{|\s)', line)]
        return sum(values) if values else None
    raw['received'] = metric('aim_http_received_requests_total')
    raw['active'] = metric('aim_http_active_requests')
    # Ausência de fila de NEGÓCIO no código da aplicação, não medição do backlog TCP.
    raw['queued'] = 0
    raw['queue_provenance'] = 'no_application_job_queue_by_architecture'
    status,_ = base.fetch('http://'+service+':8000/health')
    raw['available'] = status == 200
    return raw


base.snapshot = snapshot


def measure(service, window, rate, fraction):
    row = base.measure(service, window, rate, fraction)
    before,after = row['before'],row['after']
    received = None if before['received'] is None or after['received'] is None else after['received']-before['received']
    row.update(received=received,active_start=before['active'],active_end=after['active'],
               queued_start=before['queued'],queued_end=after['queued'],
               queue_provenance=before['queue_provenance'],available_start=before['available'],
               available_end=after['available'],scrape_valid=True,
               counter_reset=row['counter_reset'] or (received is not None and received < 0))
    return row


def main():
    started=base.utc()
    for service in base.SERVICES:
        for route in ('/work','/synthetic-failure'):
            base.fetch('http://'+service+':8000'+route)
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for window,(rate,fraction) in enumerate(zip(RATES,ERROR_FRACTIONS)):
            pending=[pool.submit(measure,service,window,rate,fraction) for service in base.SERVICES]
            rows.extend(future.result() for future in pending)
    status,collector=base.fetch('http://otel-collector:8889/metrics')
    if status!=200:
        raise RuntimeError('Snapshot Collector falhou')
    print(json.dumps(dict(capture_version='activity-capture-v1',source_kind='real_kubernetes_synthetic_workload',
        start_utc=started,end_utc=base.utc(),rows=rows,rates=RATES,error_fractions=ERROR_FRACTIONS,
        collector_prometheus=collector,notes=[
            'Entradas medidas no handler; health e metrics excluídas.',
            'Fila de negócio inexistente por arquitetura; fila TCP/rede não observada.',
            'Disponibilidade verificada por health nos limites, não continuamente.',
            'Dois períodos sem carga do cliente por serviço.',
            'Trabalho bloqueado sem novas entradas é caso sintético nos testes matemáticos, não injetado nesta coleta.',
            'O cliente sequencial espera concluir chamadas antes do snapshot final.',
            'Carga /work grava eventos sintéticos no banco existente; 404 deliberados.']),indent=2))


if __name__=='__main__': main()
