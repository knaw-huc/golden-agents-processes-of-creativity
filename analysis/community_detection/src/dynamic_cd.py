from multiprocessing.sharedctypes import Value
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
from cdlib import TemporalClustering
from matplotlib import cm
from matplotlib import colors
from collections import Counter

from pandas import describe_option




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


# Given a graph and a start and end time, create a snapshot of the graph for that interval
def create_graph_snapshot(G, start, end):
    G_snapshot = nx.Graph(earliest_time=start, latest_time=end)

    for edge in G.edges():
        # G_snapshot.add_nodes_from([edge[0],edge[1]])
        avg_time = G[edge[0]][edge[1]]['at']
        for time in avg_time:
            if time >= start and time <= end:
                if G_snapshot.has_edge(edge[0], edge[1]):
                    G_snapshot[edge[0]][edge[1]]['weight'] += 1
                else:
                    G_snapshot.add_edge(edge[0], edge[1], weight=1, books=G[edge[0]][edge[1]]['books'], bt=G[edge[0]][edge[1]]['bt'], 
                    et= G[edge[0]][edge[1]]['et'])
    return G_snapshot



# Create a set of graphs based on the given interval and stepsize, i.e. a snapshot graph
def create_snapshot_graph(G, interval, stepsize):
    earliest = G.graph['earliest_time']
    latest = G.graph['latest_time']
    curr_timestamp = earliest   
    snapshots = []
    snapshot_times = []

    while curr_timestamp < latest:
        start = curr_timestamp
        end = curr_timestamp + interval
        G_snapshot = create_graph_snapshot(G, start, end)
        if (len(G_snapshot.edges()) > 0):            
            snapshots.append(G_snapshot)
            snapshot_times.append((start, end))
        curr_timestamp = start + stepsize

    print(f"Interval: {interval}, Stepsize: {stepsize}")    
    print(f"Num of snapshots: {len(snapshots)}")   
    return (snapshots, snapshot_times)


def list_to_dict(partition):
    partition_dict = {}
    community_id = 0
    for community in partition:
        for node in community:
            partition_dict[node] =  community_id
        community_id += 1



# Perform community detection for every snapshot in the snapshot graph, using one of three Louvain variations
def dynamic_community_detection(snapshots, snapshot_times, parameters, randomize, use_init_partition, use_init_partition_randomize):
    tc = TemporalClustering()
    last_partition = None
    for index, snapshot in enumerate(snapshots):
        # nx.draw_networkx(snapshots[index], with_labels=False, node_size=40)
        plt.show()
        if randomize:
            best_coms = algorithms.louvain(snapshot, randomize=None)
            best_mod = evaluation.newman_girvan_modularity(snapshot, best_coms).score
            for x in range(10):
                coms = algorithms.louvain(snapshot, randomize=None)  # here any CDlib algorithm can be applied
                mod = evaluation.newman_girvan_modularity(snapshot, coms).score
                print(f"Mod: {mod}")
                if mod > best_mod:
                    best_coms = coms
                    best_mod = mod
            coms = best_coms
        elif use_init_partition:
            if last_partition is not None:
                coms = algorithms.louvain(snapshot, partition=list_to_dict(last_partition.communities))  # here any CDlib algorithm can be applied
                last_partition = coms  
            else:
                coms = algorithms.louvain(snapshot)
                last_partition = coms  # here any CDlib algorithm can be applied
        elif use_init_partition_randomize:
            if last_partition is not None:
                coms = algorithms.louvain(snapshot, partition=list_to_dict(last_partition.communities))  # here any CDlib algorithm can be applied
                last_partition = coms  
            else:
                best_coms = algorithms.louvain(snapshot, randomize=None)
                best_mod = evaluation.newman_girvan_modularity(snapshot, best_coms).score
                for x in range(10):
                    coms = algorithms.louvain(snapshot, randomize=None)  # here any CDlib algorithm can be applied
                    mod = evaluation.newman_girvan_modularity(snapshot, coms).score
                    print(f"Mod: {mod}")
                    if mod > best_mod:
                        best_coms = coms
                        best_mod = mod
                last_partition = best_coms                
        else:
            coms = algorithms.louvain(snapshot)
            
        mod = evaluation.newman_girvan_modularity(snapshot, coms).score
        if(mod > 0):
            tc.add_clustering(coms, index)
        
    jaccard = lambda x, y:  len(set(x) & set(y)) / len(set(x) | set(y))
    digraph = None
    stability_trend = None
    return (digraph, stability_trend, tc, snapshots, snapshot_times)



def execute_dcd(sgs, key):
    print(f"Handling sg with parameters: {key}" )
    dcd_init_partition = dynamic_community_detection(sgs[0], sgs[1], key, randomize=False, use_init_partition=True, use_init_partition_randomize=False)

    tc = dcd_init_partition[2]
    snapshots = dcd_init_partition[3]
    snapshot_times = dcd_init_partition[4]

    return (dcd_init_partition, tc, snapshots, snapshot_times)
        

# Gieven a clustered set of snapshot, match the communities in the snapshot graph to obtain dynamic communities
def matching(tc, theta):
    jaccard = lambda x, y:  len(set(x) & set(y)) / len(set(x) | set(y))
    dynamic_coms = {}
    fronts = {}
    timesteps = tc.get_observation_ids()
    init_clustering = tc.get_clustering_at(timesteps[0]).communities
    uid = 0

    # Create a dynamic community for every cluster at the first timestep and add them to the fronts of the dynamic communities
    for index, comm in enumerate(init_clustering):
        dynamic_coms[uid] = [str(timesteps[0]) + "_" + str(index)]
        fronts[uid] = str(timesteps[0]) + "_" + str(index)
        uid += 1
    
    # For each subsequent timestep, get all communities and match them with all fronts,
    # adding them if their simmilarity is higher than theta
    for t in timesteps[1:]:
        t_clustering = tc.get_clustering_at(t).communities
        for index, comm in enumerate(t_clustering):
            matches = []
            for front_id, front_comm in fronts.items():
                sim = jaccard(comm, tc.get_community(front_comm))
                if sim >= theta:
                    matches.append(front_id)
            if len(matches) == 0:
                dynamic_coms[uid] = [str(t) + "_" + str(index)]
                fronts[uid] = str(t) + "_" + str(index)
                uid += 1
            else:
                if len(matches) > 1:
                    print(f"MERGING {matches}")
                for match in matches:
                    if fronts[match].split()[0] == str(t):
                        print("SPLIT")
                        dynamic_coms[uid] = dynamic_coms[match][:-1].append(str(t) + "_" + str(index))
                        fronts[uid] = str(t) + "_" + str(index)
                        uid += 1
                    else:
                        dynamic_coms[match].append(str(t) + "_" + str(index))
                        fronts[match] = str(t) + "_" + str(index)
    return dynamic_coms


# Print the given dynamic community, iterating through al it's static communities in all timesteps it exists
def print_dyn_com(dynamic_coms, id, tc, snapshots, snapshot_times):
    dynamic_com = dynamic_coms[id]
    cache_folder = Path("./cache/")    
    file_to_check = cache_folder / "attribute_cache.gpickle"
    if not file_to_check.exists():
        attribute_cache = {}
    else:
        attribute_cache = nx.read_gpickle(cache_folder / "attribute_cache.gpickle")

    for part in dynamic_com:
        part_timestep = part.split('_')[0]
        com_id = part.split('_')[1]
        partition = tc.get_clustering_at(int(part_timestep)).communities
        snapshot = snapshots[int(part_timestep)]
        com = partition[int(com_id)]
        interval = snapshot_times[int(part_timestep)]
        print(interval)
        print_dc(tc, dynamic_coms, int(part_timestep), com_id, None, id, snapshots, snapshot_times)
        
         # Get degree centralities
        degree_centrality = nx.degree_centrality(snapshots[int(part_timestep)])
        dc_centrality_dict = {}
        for node in com:
            if node in attribute_cache:
                com_name = attribute_cache[node]
            else:
                com_name = getName(node)
                attribute_cache[node] = com_name
            dc_centrality_dict[node] = (degree_centrality[node], com_name)
        
        dc_centrality_dict_sorted = sorted(dc_centrality_dict.items(), key=lambda item: item[1], reverse=True)

        for value in dc_centrality_dict_sorted:
            print(f"{value[1][1]} - Centrality: {round(value[1][0], 3)} - URI: {value[0]}")
        print("-------------------------")

def match_dyn_com(dynamic_coms, id):
    for dyn_id, coms in dynamic_coms.items():
        if id in coms:
            return dyn_id

# Given a community id, print the snapshot its in and colour only that community
def print_dc(tc, dynamic_coms, t, com_id, name, dyn_com_id, snapshots, snapshot_times):
    cmap = cm.get_cmap('hsv', 10)
    norm = colors.Normalize(vmin=0, vmax=len(dynamic_coms.keys()))
    partition = tc.get_clustering_at(t).communities
    graph = snapshots[t]
    position = nx.spring_layout(graph, seed=7)  # compute graph layout
    n_communities = len(partition)
    node_size = 120

    plt.figure(figsize=(10, 10))
    plt.rcParams['figure.facecolor'] = 'white'
    plt.title(str(snapshot_times[t]))

    filtered_nodelist = list(np.concatenate(partition))
    filtered_edgelist = list(
        filter(
            lambda edge: len(np.intersect1d(edge, filtered_nodelist)) == 2,
            graph.edges(),
        )
    )
    fig = nx.draw_networkx_nodes(
        graph, position, node_size=node_size, node_color="w", nodelist=filtered_nodelist
    )
    fig.set_edgecolor("k")
    nx.draw_networkx_edges(graph, position, alpha=0.5, edgelist=filtered_edgelist)

    for i in range(n_communities):
            if len(partition[i]) > 0:
                size = node_size
                fig = nx.draw_networkx_nodes(
                graph,
                position,
                node_size=size,
                nodelist=partition[i],
                node_color=[get_color(i, com_id, name, dyn_com_id, cmap)],
            )
            fig.set_edgecolor("k")
    plt.show()


def get_color(i, com_id, name, dyn_com_id, cmap):
    if i == int(com_id):
        return cmap((int(dyn_com_id) % 10))
    else:
        return 'white'

# Given a name, find all dynamic communities it belongs to and export them in the timesteps it belongs to them
def find_dyn_com(dynamic_coms, name, tc, snapshots, snapshot_times):
    timesteps = tc.get_observation_ids()
    print(f"NAME TO FIND: {name}")
    cache_folder = Path("./src/cache/")    
    file_to_check = cache_folder / "attribute_cache.gpickle"
    if not file_to_check.exists():
        attribute_cache = {}
    else:
        attribute_cache = nx.read_gpickle(cache_folder / "attribute_cache.gpickle")

    full_com_list = []
    for timestep in timesteps:
        partition = tc.get_clustering_at(timestep).communities
        com_id = None
        # for all communities in timestep
        for index, com in enumerate(partition):
            com_index = None
            for node in com:
                if node in attribute_cache:
                    com_name = attribute_cache[node]
                else:
                    com_name = getName(node)
                    attribute_cache[node] = com_name
                if com_name == name:
                    com_index = index
                    break
            if com_index is not None:
                com_id = com_index
                break
        if com_id is not None:
            full_com_id = str(timestep) + '_' + str(com_id)
            full_com_list.append(full_com_id)
            print(full_com_id)

    for full_com_id in full_com_list:
        timestep = int(full_com_id.split('_')[0])
        print(f"TIMESTEP: {timestep}")
        com_id = full_com_id.split('_')[1]
        dyn_com_id = match_dyn_com(dynamic_coms, full_com_id)
        print(f"DYNAMIC COMMUNITY: {dyn_com_id}")
        partition = tc.get_clustering_at(timestep).communities
        com = partition[int(full_com_id.split('_')[1])]
    
        # Get degree centralities
        degree_centrality = nx.degree_centrality(snapshots[timestep])

        interval = snapshot_times[timestep]
        print(f"INTERVAL {interval}")
        print_dc(tc, dynamic_coms, timestep, com_id, name, dyn_com_id, snapshots, snapshot_times)

        # Dictionary for storing and sorting degree centralities and names
        dc_centrality_dict = {}
        for node in com:
            if node in attribute_cache:
                com_name = attribute_cache[node]
            else:
                com_name = getName(node)
                attribute_cache[node] = com_name

            dc_centrality_dict[node] = (degree_centrality[node], com_name)
        dc_centrality_dict_sorted = sorted(dc_centrality_dict.items(), key=lambda item: item[1], reverse=True)

        for value in dc_centrality_dict_sorted:
            print(f"{value[1][1]} - Centrality: {round(value[1][0], 3)} - URI:{value[0]}")
    
        print("-------------------------------------------------------------")



def get_attributes(uri):
    sparql = SPARQLWrapper("https://sparql.goldenagents.org/sparql")
    query = f"""PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>
        PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#> 
        PREFIX schema: <http://schema.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ecartico: <http://www.vondel.humanities.uva.nl/ecartico/lod/vocab/#>
        SELECT * WHERE {{
                GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {{
                    OPTIONAL {{<{uri}> a schema:Person ;
                        schema:birthPlace ?birthPlace .
                
                    ?birthPlace a schema:Place ;
                    schema:name ?birthPlaceName }} .
                }}
                GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {{
                    OPTIONAL {{ <{uri}> a schema:Person ;
                                    ecartico:religion ?religionName }} .
                }}
            }}"""
    sparql.setReturnFormat(JSON)
    sparql.setQuery(query)
    query_results = sparql.queryAndConvert()
    structured_results = query_results["results"]["bindings"]
    return structured_results


# Get the union of all nodes for all communities within a dynamic community
def get_community_union(tc, snapshots, snapshot_times, dynamic_coms, dynamic_com_id):
    dynamic_com = dynamic_coms[dynamic_com_id]
    union_community = [] 

    for part in dynamic_com:
        part_timestep = part.split('_')[0]
        com_id = part.split('_')[1]
        partition = tc.get_clustering_at(int(part_timestep)).communities
        snapshot = snapshots[int(part_timestep)]
        com = partition[int(com_id)]
        union_community += com
        
    return union_community

# Given a community (list of nodes), get a simple description for it using ndoe attributes
def get_community_description(community):
    # Get attributes for community member
    attributes = {}
    religion = []
    birthplace = []
    for uri in community:
        attr = get_attributes(uri)
        attributes[uri] = attr
        if 'birthPlaceName' in attr[0]:
            birthplace.append(attr[0]['birthPlaceName']['value'])
        if 'religionName' in attr[0]:
            religion.append(attr[0]['religionName']['value'])

    c_birthplace = Counter(birthplace)
    birthplace_common = c_birthplace.most_common(1)

    c_religion = Counter(religion)
    religion_common = c_religion.most_common(1)

    return (birthplace_common, religion_common)


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