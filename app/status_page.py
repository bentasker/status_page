#!/usr/bin/env python3

'''
pip install influxdb-client prefect
'''
import json
import sys

import warnings

from influxdb_client import InfluxDBClient
from influxdb_client.client.warnings import MissingPivotFunction
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
def get_response_times_by_region(query_api, url):
    logger = get_run_logger()

    # Silence the pivot warning - data is already in wide format
    warnings.simplefilter("ignore", MissingPivotFunction)
    query = f'''
                data = from(bucket: "Systemstats")
                |> range(start: -6h)
                |> filter(fn: (r) => r["_measurement"] == "http_response")
                |> filter(fn: (r) => r["_field"] == "response_time")
                |> filter(fn:(r) => r["server"] == "{url}")
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
    result = query_api.query(query)

    response_times = []
    for table in result:
        for row in table.records:
            response_times.append({
                "region" : row.values["region"],
                "min" : row.values["min"],
                "max" : row.values["max"],
                "mean" : row.values["mean"],
                "p95" : row.values["p95"]
                })

    return response_times


@task(retries=3, retry_delay_seconds=2)
def get_response_times(query_api, url):
    logger = get_run_logger()
    query = f'''
        from(bucket: "Systemstats")
        |> range(start: -6h)
        |> filter(fn: (r) => r["_measurement"] == "http_response")
        |> filter(fn: (r) => r["_field"] == "response_time")
        |> filter(fn: (r) => r["server"] == "{url}")
        |> group(columns: ["region", "server", "_field"])
        |> aggregateWindow(every: 15m, fn: mean, createEmpty: false)
        |> map(fn: (r) => ({{
            _time: r._time,
            _field: r._field,
            _value: r._value * 1000.0,
            region: r.region,
            server: r.server
        }}))
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    result = query_api.query(query)
    print(query)

    response_times = []
    for table in result:
        for row in table.records:
            response_times.append({
                "time" : row.values["_time"].strftime('%Y-%m-%d %H:%M:%S'),
                "region" : row.values["region"],
                "response_time" : row.values["response_time"]
                })

    return response_times



@flow(retries=3, retry_delay_seconds=10)
def main():
    # TODO: replace with secret storage
    token = sys.argv[1]
    edge_url = "https://www.bentasker.co.uk"
    origin_url = "https://mailarchives.bentasker.co.uk/gone.html"

    logger = get_run_logger()

    # Stand up the client
    client = InfluxDBClient(url="https://eu-central-1-1.aws.cloud2.influxdata.com", token=token, org="")
    query_api = client.query_api()

    resp_object = {}


    resp_object["edge_status"] = get_service_status(query_api, "https://www.bentasker.co.uk")
    resp_object["origin_status"] = get_service_status(query_api, "https://mailarchives.bentasker.co.uk/gone.html")

    resp_object["edge_response_times"] = get_response_times(query_api, "https://www.bentasker.co.uk")
    resp_object["origin_response_times"] = get_response_times(query_api, "https://mailarchives.bentasker.co.uk/gone.html")

    resp_object["edge_responses_by_region"] = get_response_times_by_region(query_api, "https://www.bentasker.co.uk")
    resp_object["origin_responses_by_region"] = get_response_times_by_region(query_api, "https://mailarchives.bentasker.co.uk/gone.html")

    json_op = json.dumps(resp_object)
    logger.info(json_op)

    fh = open("output.json", "w")
    fh.write(json_op)
    fh.close()




if __name__ == "__main__":
    main()
