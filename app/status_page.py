#!/usr/bin/env python3


import sys

from influxdb_client import InfluxDBClient
from prefect import flow, get_run_logger



@flow(retries=3, retry_delay_seconds=10)
def main():
    # TODO: replace with secret storage
    token = sys.argv[1]

    logger = get_run_logger()

    # Stand up the client
    client = InfluxDBClient(url="https://eu-central-1-1.aws.cloud2.influxdata.com", token=token, org="")
    query_api = client.query_api()


    tables = query_api.query('from(bucket:"Systemstats") |> range(start: -10m) |> filter(fn: (r) => r._measurement == "http_response")')
    logger.info("hello world")
    for table in tables:
        for row in table.records:
            logger.info(row.values)




if __name__ == "__main__":
    main()
