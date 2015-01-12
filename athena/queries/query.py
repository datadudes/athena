import os

from tabulate import tabulate
import yaml

from athena.queries import query_impala
from athena.queries import query_to_csv


def execute_query(sql, csv_file=None):
    if not csv_file:
        results, field_names = query_impala(sql)
        return tabulate(results, headers=field_names, tablefmt="simple", numalign='left')
    else:
        query_to_csv(sql, csv_file=csv_file)
        return "The results have succesfully been written to '{}'".format(os.path.basename(csv_file))


def parse_yaml_queries(yaml_file):
    queries = yaml.load(yaml_file)
    for query in queries:

        items = query.get("with_items")
        sql = query.get('query')
        filename = query.get('output')

        if items is None:
            print("\n- Executing query '{}'\n".format(sql))
            print(execute_query(sql, filename))
        else:
            for item in items:
                sql_instance = sql.replace("{{ item }}", item)
                filename_instance = filename.replace("{{ item }}", item)
                print("\n- Executing query '{}' with parameters '{}'\n".format(sql_instance, filename_instance))
                print(execute_query(sql_instance, filename_instance))
