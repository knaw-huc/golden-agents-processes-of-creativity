import sys
import time
from typing import Union

import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE

from rdflib import ConjunctiveGraph, Dataset
from rdflib.graph import Graph


def query(
    q: str,
    endpoint: str,
    OFFSET: int = 0,
    LIMIT: int = 10000,
    graph: ConjunctiveGraph = None
) -> Union[pd.DataFrame, ConjunctiveGraph, None]:

    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(q + f" OFFSET {OFFSET} LIMIT {LIMIT}")

    if sparql.queryType == "SELECT":
        sparql.setReturnFormat(JSON)

        results = sparql.query().convert()

        df = pd.DataFrame(results['results']['bindings'])
        df = df.applymap(lambda x: x['value'] if not pd.isna(x) else "")

        if len(df) == LIMIT:

            OFFSET += LIMIT
            #time.sleep(1)

            new_df = query(q, endpoint, OFFSET, LIMIT)
            df = df.append(new_df)

        return df

    elif sparql.queryType == "CONSTRUCT":
        sparql.setReturnFormat(TURTLE)

        results = sparql.query().convert()

        if graph is None:
            graph = ConjunctiveGraph()

        graph.parse(data=results, format="turtle")

        if 'Empty TURTLE' not in results.decode('utf-8'):
            OFFSET += LIMIT
            #time.sleep(1)

            graph = query(q, endpoint, OFFSET, LIMIT, graph)

        return graph

    else:
        print("Query type not supported")


if __name__ == "__main__":

    qfile = sys.argv[1]
    target = sys.argv[2]

    with open(qfile, 'r') as f:
        q = f.read()

    data = query(q, "https://sparql.goldenagents.org/sparql")

    if isinstance(data, pd.DataFrame):
        data.to_csv(target, sep='\t', index=False)
    else:
        data.serialize(target, format="turtle")
