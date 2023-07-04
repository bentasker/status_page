#!/usr/bin/env python3


import sys

from influxdb_client import InfluxDBClient
from prefect import flow, task, get_run_logger


@task(retries=3, retry_delay_seconds=1)
def get_service_status(query_api, url):
    ''' Run a flux query and calculate a textual description of service status
    '''
    # Default result
    state = "Unknown"

    logger = get_run_logger()
    query = f'''
        from(bucket: "Systemstats")
        |> range(start: -30m)
        |> filter(fn: (r) => r["_measurement"] == "http_response")
        |> filter(fn: (r) => r["_field"] == "response_status_code_match")
        |> filter(fn: (r) => r["server"] == "{url}")
        |> last()
        |> group()
        |> mean()
    '''

    tables = query_api.query(query)
    for table in tables:
        for row in table.records:
            if row.values['_value'] == 1:
                state = "Up"
            elif row.values['_value'] < 1 and row.values['_value'] > 0.75:
                state = "Mostly Up"
            elif row.values['_value'] < 0.75 and row.values['_value'] > 0.5:
                state = "Degraded"
            else:
                state = "Down"

    logger.info(f"{url} is {state}")
    return state

@task(retries=3, retry_delay_seconds=1)
def get_response_times(query_api, url):
    logger = get_run_logger()
    query = f'''
                data = from(bucket: "Systemstats")
                |> range(start: -6h)
                |> filter(fn: (r) => r["_measurement"] == "http_response")
                |> filter(fn: (r) => r["_field"] == "response_time")
                |> filter(fn:(r) => r["server"] == "https://www.bentasker.co.uk")
                |> group(columns: ["region"])
                |> map(fn:(r) => ({{r with _value: r._value * 1000.0}}))
                |> keep(columns: ["_value", "region"])

                mean = data
                |> mean()

                max = data
                |> max()

                min = data
                |> min()

                p95 = data
                |> quantile(q:0.95)


                j1 = join(tables: {{ mean: mean, max: max }},
                    on: ["region"],
                    method: "inner"
                )

                j2 = join(tables: {{ min: min, j1: j1 }},
                    on: ["region"],
                    method: "inner"
                    )

                join(tables: {{ min: j2, perc: p95 }},
                    on: ["region"],
                    method: "inner"
                    )
                    |> map(fn: (r) => ({{
                    region: r.region,
                    min: r._value_min,
                    max: r._value_max,
                    mean: r._value_mean,
                    p95: r._value_perc
                    }}))
                    |> group()

    '''
    tables = query_api.query(query)
    return tables


@flow(retries=3, retry_delay_seconds=10)
def main():
    # TODO: replace with secret storage
    token = sys.argv[1]

    logger = get_run_logger()

    # Stand up the client
    client = InfluxDBClient(url="https://eu-central-1-1.aws.cloud2.influxdata.com", token=token, org="")
    query_api = client.query_api()

    edge_status = get_service_status(query_api, "https://www.bentasker.co.uk")
    origin_status = get_service_status(query_api, "https://mailarchives.bentasker.co.uk/gone.html")

    edge_responses = get_response_times(query_api, "https://www.bentasker.co.uk")
    origin_responses = get_response_times(query_api, "https://mailarchives.bentasker.co.uk/gone.html")

if __name__ == "__main__":
    main()
