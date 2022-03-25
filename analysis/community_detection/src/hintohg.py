import io
from socket import getnameinfo
from xml.etree import ElementTree
import requests

import scipy.stats as st
from matplotlib import colors
import numpy as np
from pathlib import Path
import os

from rdflib import Graph, ConjunctiveGraph, Namespace, OWL, Literal, URIRef, BNode, XSD, RDFS, RDF
from SPARQLWrapper import SPARQLWrapper, JSON

import networkx as nx
from cdlib import algorithms
import matplotlib.pyplot as plt
from cdlib import evaluation

from cdlib.algorithms import louvain
from cdlib import algorithms, viz


def import_HIN():     
    # Create a Graph
    g = Graph()

    # Parse in the RDF (.ttl) file 
    g.parse("./../data/all-schema-ecartico.ttl.txt")

    # Loop through each triple in the graph (subj, pred, obj)
    for subj, pred, obj in g:
        # Check if there is at least one triple in the Graph
        if (subj, pred, obj) not in g:
            raise Exception("Something went wrong!")
    
    # Print the number of "triples" in the Graph
    print(f"The graph has {len(g)} statements.")
    return g


def getName(uri):
    sparql = SPARQLWrapper("https://sparql.goldenagents.org/sparql")
    sparql.setQuery (f"""
        SELECT ?s ?t
        WHERE {{ OPTIONAL {{ <{uri}> <http://schema.org/name> ?t}} }}
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    name = list(results["results"]["bindings"][0].values())[0]["value"]
    print (name)
    return name

# Create a homogeneous graph based on a given metapath, using the locally stored rdf graph
def rdf_to_homogeneous(g, metapath):
    query_results = g.query(metapath)

    avg_time = int((list(query_results)[0].et.toPython().year + list(query_results)[0].bt.toPython().year) / 2)
    earliest_time = avg_time
    latest_time = avg_time
    G = nx.Graph(earliest_time=avg_time, latest_time=avg_time)

    print(f"Number of meta-path instances: {len(list(query_results))}")

    # Create a homogeneous graph for a given set of meta-path instances
    for row in query_results:
        avg_time = int((row.et.toPython().year + row.bt.toPython().year) / 2)

        if avg_time < earliest_time:
            earliest_time = avg_time
        elif avg_time > latest_time:
            latest_time = avg_time

        if (G.has_edge(str(row.w1), str(row.w2))):
            G[str(row.w1)][str(row.w2)]['weight'] += 1
            G[str(row.w1)][str(row.w2)]['books'].add(Book(row.b, None, row.bt, row.et))
            G[str(row.w1)][str(row.w2)]['bt'].append(row.bt.toPython().year)
            G[str(row.w1)][str(row.w2)]['et'].append(row.et.toPython().year)
            G[str(row.w1)][str(row.w2)]['at'].append(avg_time)

        else:
            G.add_edge(str(row.w1), str(row.w2), weight=1, books= {Book(row.b, None
            , row.bt, row.et)}, bt=[row.bt.toPython().year], et=[row.et.toPython().year], at= [avg_time])

    print(f"Num of edges {len(G.edges)}")
    print(f"Num of nodes {len(G.nodes)}")
    G.graph['earliest_time'] = earliest_time
    G.graph['latest_time'] = latest_time
    return G

# Create a homogeneous graph based on a given metapath, using the goldenagents endpoint
def rdf_to_homogeneous_endpoint(query):
    print("Creating homogenous graph...")
    sparql = SPARQLWrapper("https://sparql.goldenagents.org/sparql")
    sparql.setReturnFormat(JSON)
    sparql.setQuery(query)
    query_results = sparql.queryAndConvert()

    structured_results = query_results["results"]["bindings"]
    avg_time = int((int(structured_results[0]['et']['value'].split('-')[0]) + int(structured_results[0]['bt']['value'].split('-')[0])) / 2)
    earliest_time = avg_time
    latest_time = avg_time
    G = nx.Graph(earliest_time=avg_time, latest_time=avg_time)

    print(f"Number of meta-path instances: {len(list(structured_results))}")

    # Create a homogeneous graph for a given set of meta-path instances
    for row in structured_results:
        w1 = row['w1']['value']
        w2 = row['w2']['value']     
        avg_time = int((int(row['et']['value'].split('-')[0]) + int(row['bt']['value'].split('-')[0])) / 2)

        if avg_time < earliest_time:
            earliest_time = avg_time
        elif avg_time > latest_time:
            latest_time = avg_time

        if (G.has_edge(w1, w2)):
            G[w1][w2]['weight'] += 1
            G[w1][w2]['books'].add(Book(row['b']['value'], None, 
            row['bt']['value'], row['et']['value']))
            G[w1][w2]['bt'].append(row['bt']['value'].split('-')[0])
            G[w1][w2]['et'].append(row['et']['value'].split('-')[0])
            G[w1][w2]['at'].append(avg_time)

        else:
            G.add_edge(w1, w2, weight=1, books= {Book(row['b']['value'], None
            ,  row['bt']['value'],  row['et']['value'])}, bt=[row['bt']['value'].split('-')[0]], et=[row['et']['value'].split('-')[0]], at= [avg_time])

    print(f"Num of edges {len(G.edges)}")
    print(f"Num of nodes {len(G.nodes)}")
    G.graph['earliest_time'] = earliest_time
    G.graph['latest_time'] = latest_time
    return G    

class Book:
    def __init__(self, uri, name, bt, et):
        self.uri = uri
        self.name = name
        self.bt = bt
        self.et = et

    def __hash__(self):
        return hash((self.uri))

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.uri == other.uri