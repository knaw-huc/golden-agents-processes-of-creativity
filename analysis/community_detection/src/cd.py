from operator import truediv
from socket import getnameinfo
import networkx as nx
from cdlib import algorithms
import matplotlib.pyplot as plt
from cdlib import evaluation
from SPARQLWrapper import SPARQLWrapper, JSON
import os
from cdlib.algorithms import louvain
from cdlib import algorithms, viz
from pathlib import Path
import csv
import numpy as np

sparql = SPARQLWrapper("https://sparql.goldenagents.org/sparql")

def getName(uri):
    sparql.setQuery (f"""
        SELECT ?s ?t
        WHERE {{ OPTIONAL {{ <{uri}> <http://schema.org/name> ?t}} }}
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    return list(results["results"]["bindings"][0].values())[0]["value"]

def getBookSet(g, cluster_edges):
    bookset = set([])
    # count = 0

    for edge in cluster_edges:
        # count += len(g[edge[0]][edge[1]]['books'])
        bookset |= g[edge[0]][edge[1]]['books']
      
    return (len(bookset), bookset)

# Get the earliest timestamp and the latest timestamp of a set of edges of a community
def getMinMaxDates(g, cluster_edges):
    earliestList = []
    latestList = []

    for edge in cluster_edges:
        for year in g[edge[0]][edge[1]]['bt']:
            earliestList.append(year)    
        for year in g[edge[0]][edge[1]]['et']:
            latestList.append(year)

  
    bins = 10
    if len(earliestList) > 11:
        mean_earliest = np.mean(earliestList)
        std_earliest = np.std(earliestList)
        earliest_time = mean_earliest - (2 * std_earliest)
    else:
        earliest_time = min(earliestList)

    if len(latestList) > 11:
        mean_latest = np.mean(latestList)
        std_latest = np.std(latestList)
        latest_time = mean_latest + (2 * std_latest)
    else:
        latest_time = max(latestList)


        
    # plt.hist(earliestList, bins=bins, color='darkblue', edgecolor='white');
    # plt.hist(latestList, bins=bins, color='darkblue', edgecolor='white');
    # plt.show()
    return (int(earliest_time), int(latest_time))
    # return (mean_earliest)


def edgeInCluster(edge, cluster):
    if edge[1] in list(cluster):
        return True
    return False

# Get the largest connected component of a graph
def getLCC(hg):
    components = nx.connected_components(hg)
    largest_subgraph_size = max(components, key=len)
    lcc = hg.subgraph(largest_subgraph_size)
    return lcc

def community_detection_louvain(g):
    g_lcc = getLCC(g)

    # Perform the louvain commiunity detecion algorithm on the homogeneous graph
    louvain_communities = louvain(g)
    mod_louvain = louvain_communities.newman_girvan_modularity()
    avg_embeddedness_louvain = evaluation.avg_embeddedness(g,louvain_communities)
    
    # Perform the louvain commiunity detecion algorithm on the LCC of the homogeneous graph
    louvain_communities_lcc = louvain(g_lcc)
    mod_louvain_lcc = louvain_communities_lcc.newman_girvan_modularity()
    avg_embeddedness_louvain_lcc = evaluation.avg_embeddedness(g_lcc,louvain_communities_lcc)

    # Print some analysis on the resulting clustering
    print(f"Number of communities (louvain): {len(louvain_communities.communities)}")
    print(f"Number of communities (louvain_lcc): {len(louvain_communities_lcc.communities)}")
    print()
    print(f"Modularity (louvain): {mod_louvain}")
    print(f"Modularity (louvain lcc): {mod_louvain_lcc}")
    print()
    print(f"Average Embeddedness (louvain): {avg_embeddedness_louvain}")
    print(f"Average Embeddedness (louvain lcc): {avg_embeddedness_louvain_lcc}")

    # Draw the communities
    fig = plt.figure(1)
    viz.plot_network_clusters(g, node_size=150, partition=louvain_communities)
    viz.plot_network_clusters(g_lcc, node_size=150, partition=louvain_communities_lcc)
    plt.show()

    return (louvain_communities, louvain_communities_lcc)


# For each community, add all nodes to a dict along with their centrality measure,
# sort this dict based on centrality, and add the dict to a list of communities
def format_partition(g, coms): 
    dc_sorted_communities_list = []
    degree_centrality = nx.degree_centrality(g)
    cache_folder = Path("./cache/")    
    file_to_check = cache_folder / "attribute_cache.gpickle"
    is_cached = None
    if not file_to_check.exists():
        is_cached = False
        attribute_cache = {}
            # print("HG saved in folder \"homogeneous_graphs\"")
    else:
        is_cached = True
        attribute_cache = nx.read_gpickle(cache_folder / "attribute_cache.gpickle")
            # print("HG imported")

    for cluster in coms.communities:
        dc_centrality_dict = {}
        cluster_edges = []
        for node in cluster:
            edges = g.edges(node)
            for edge in edges:
                if edgeInCluster(edge, cluster):
                    cluster_edges.append(edge)
            if node in attribute_cache:
                name = attribute_cache[node]
            else:
                name = getName(node)
                attribute_cache[node] = name
            # print(name)
            # g[edge[0]][edge[1]]['books']
            dc_centrality_dict[node] = (degree_centrality[node], name)

        dc_centrality_dict_sorted = sorted(dc_centrality_dict.items(), key=lambda item: item[1], reverse=True)
        min_max_dates = getMinMaxDates(g, 
        cluster_edges)
        (bookcount, bookset) =  getBookSet(g, cluster_edges)
        # print(f"Number of books:  {bookcount}")
        print(f"Number of books (length):  {len(bookset)}")

        for book in bookset:
            if book.uri in attribute_cache:
                book_name = attribute_cache[book.uri]
            else:
                book_name = getName(book.uri)
                attribute_cache[book.uri] = book_name
            print(book_name)

        dc_sorted_communities_list.append((dc_centrality_dict_sorted, min_max_dates, bookset, bookcount))
    if not is_cached:
        nx.write_gpickle(attribute_cache, cache_folder / "attribute_cache.gpickle")
    return (dc_sorted_communities_list, attribute_cache)


# Export results
def export(sorted_communities, metapath_name, attribute_cache):
    data_folder = Path("results/")

    # Export topx community list
    filename =  metapath_name + "_expo.txt"
    file_to_write = data_folder / filename
    os.makedirs(os.path.dirname(file_to_write), exist_ok=True)
    with open(file_to_write, mode='w') as communities:
        for index1, community in enumerate(sorted_communities):
            communities.write(f"Community {index1+1}, total members of the community: {len(community[0])}, Period: {community[1]}, Number of books: {community[3]}")
            communities.write('\n')
            communities.write("Top 5 nodes according to degree centrality:")
            communities.write('\n')
            top5 = list(community[0])[:5]
            for index2, person in enumerate(top5):
                uri = person[0]
                cm = person[1][0]
                name = person[1][1]
                communities.write(f"{index2} : {name}, CM: {round(cm, 3)} (URI: {uri})")
                communities.write('\n')

            communities.write('\n')
            communities.write('\n')
        print(f"File {metapath_name}_expo.txt' created.")

    # Export full community list
    filename =  metapath_name + ".csv"
    file_to_write = data_folder / filename
    with open(file_to_write, mode='w') as communities:
        fieldnames = ["Community", "Name", "Centrality Measure", "URI", "Community Period"]
        coms_writer = csv.writer(communities, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        coms_writer.writerow(fieldnames)

        for index1, community in enumerate(sorted_communities):
            # print(community)
            for index2, person in enumerate(community[0]):
                # print(person)
                uri = person[0]
                cm = person[1][0]
                name = person[1][1]
                period = community[1]
                # print(f"{index2} : {name}, DC: {cm} (URI: {uri})")
                # print(f"{index2} : {name}, DC: {n[1]} (URI: {n[0]})")
                coms_writer.writerow([index1 + 1, name, round(cm, 3), uri, period])
        print(f"File {metapath_name}.csv' created.")

    
    # Export community attributes list
    filename =  metapath_name + "_attributes.csv"
    file_to_write = data_folder / filename
    os.makedirs(os.path.dirname(file_to_write), exist_ok=True)
    with open(file_to_write, mode='w') as communities:
        coms_writer = csv.writer(communities, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for index1, community in enumerate(sorted_communities):
            coms_writer.writerow([f"Community {index1+1} - Period: ({community[1][0]} - {community[1][1]} - Number of books: {community[3]}"])
            # coms_writer.writerow()
            # communities.writerow("Books:")
            # communities.writerow('\n')
            
            coms_writer.writerow(["Name", "URI", "Begin", "End"])
            for book in community[2]:
                coms_writer.writerow([attribute_cache[book.uri], book.uri, book.bt, book.et])

        print(f"File {metapath_name}_attributes.csv' created.")