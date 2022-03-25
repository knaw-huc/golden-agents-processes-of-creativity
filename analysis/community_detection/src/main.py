import string
import hintohg
import cd
import dynamic_cd
from pathlib import Path
import networkx as nx



BIB = """PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>
                PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#> 
                PREFIX schema: <http://schema.org/>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT * WHERE {
                
                ?b schema:illustrator ?w1, ?w2 ;
                        schema:publication ?publicationEvent .
                
                # Iets expliciet maken helpt altijd voor de query-processor.
                ?publicationEvent a schema:PublicationEvent .
                
                OPTIONAL { ?publicationEvent sem:hasEarliestBeginTimeStamp ?bt}. # Typo in de STCN
                OPTIONAL { ?publicationEvent sem:hasLatestEndTimeStamp ?et}.
                # OPTIONAL { ?bt a ?type}.  # Typo in de STCN
                
                FILTER(?w1 != ?w2).
                # FILTER(xsd:integer(?bt) < 1800).
                # FILTER(?w1 < ?w2)  # RDF kent geen volgorde 
}"""
BPB = """SELECT DISTINCT ?w1 ?w2 ?bt ?et ?b
                    WHERE { 
                        ?b  <http://schema.org/publication>/<http://schema.org/publishedBy> ?w1.
                        ?b   <http://schema.org/publication>/<http://schema.org/publishedBy> ?w2.
                        ?b  <http://schema.org/publication> ?pe.
                        OPTIONAL {?pe <http://semanticweb.cs.vu.nl/2009/11/sem/hasEarliestBeginTimestamp> ?bt}.
                        OPTIONAL {?pe <http://semanticweb.cs.vu.nl/2009/11/sem/hasLatestEndTimestamp> ?et}.
                        FILTER(?w1 != ?w2).
                        FILTER(!CONTAINS(STR(?w1), 'https://data.goldenagents.org/datasets/rmlibrary/')).
                        FILTER(!CONTAINS(STR(?w2), 'https://data.goldenagents.org/datasets/rmlibrary/'))                        }"""
BCB = """SELECT DISTINCT ?w1 ?w2 ?bt ?et ?b
                    WHERE { 
                        ?b  <http://schema.org/contributor> ?w1.
                        ?b  <http://schema.org/contributor> ?w2.
                        ?b  <http://schema.org/publication> ?pe.
                        OPTIONAL {?pe <http://semanticweb.cs.vu.nl/2009/11/sem/hasEarliestBeginTimestamp> ?bt}.
                        OPTIONAL {?pe <http://semanticweb.cs.vu.nl/2009/11/sem/hasLatestEndTimestamp> ?et}.
                        FILTER(?w1 != ?w2).
                        FILTER(?w1 < ?w2).
                        FILTER(!CONTAINS(STR(?w1), 'https://data.goldenagents.org/datasets/rmlibrary/')).
                        FILTER(!CONTAINS(STR(?w2), 'https://data.goldenagents.org/datasets/rmlibrary/'))
                        }"""

BCPIB = """PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>
                PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#> 
                PREFIX schema: <http://schema.org/>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT * WHERE {
                
                ?b schema:illustrator|schema:contributor|schema:publication/schema:publishedBy ?w1, ?w2 ;
                        schema:publication ?publicationEvent .
                
                # Iets expliciet maken helpt altijd voor de query-processor.
                ?publicationEvent a schema:PublicationEvent .
                
                OPTIONAL { ?publicationEvent sem:hasEarliestBeginTimeStamp ?bt}. # Typo in de STCN
                OPTIONAL { ?publicationEvent sem:hasLatestEndTimeStamp ?et}.
                # OPTIONAL { ?bt a ?type}.  # Typo in de STCN
                
                FILTER(?w1 != ?w2).
                # FILTER(xsd:integer(?bt) < 1800).
                # FILTER(?w1 < ?w2)  # RDF kent geen volgorde 
}"""





# BCPIB = """ 
# PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>
# PREFIX schema: <http://schema.org/>
# PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
# PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
# SELECT * WHERE {
 
#   {?book schema:illustrator ?illustrator1, ?illustrator2 ;
#         schema:publication ?publicationEvent .
 
#   # Iets expliciet maken helpt altijd voor de query-processor.
#   ?publicationEvent a schema:PublicationEvent .
 
#   OPTIONAL { ?publicationEvent sem:hasEarliestBeginTimestamp ?dateBegin . } # Typo in de STCN
#   OPTIONAL { ?publicationEvent sem:hasLatestEndTimestamp ?dateEnd . } # Typo in de STCN
 
#   FILTER(?illustrator1 != ?illustrator2)
#   FILTER(?illustrator1 < ?illustrator2)}

#   UNION

#     {?book schema:contributor ?illustrator1, ?illustrator2;
#             schema:publication ?publicationEvent .
    
#     # Iets expliciet maken helpt altijd voor de query-processor.
#     ?publicationEvent a schema:PublicationEvent .
    
#     OPTIONAL { ?publicationEvent sem:hasEarliestBeginTimestamp ?dateBegin . } # Typo in de STCN
#     OPTIONAL { ?publicationEvent sem:hasLatestEndTimestamp ?dateEnd . } # Typo in de STCN
    
#     FILTER(?illustrator1 != ?illustrator2)
#     FILTER(?illustrator1 < ?illustrator2)}
#    # RDF kent geen volgorde
# }"""


metapaths = { "BCPIB" : BCPIB,
            }


def main():
    print("Community Detection in Knowledge Graphs")
    graph = hintohg.import_HIN()
    
    results = {}

    data_folder = Path("./homogeneous_graphs/") 

    # dynamic community detection
    for key, item in metapaths.items():
        file_to_check = data_folder / (key + ".gpickle")
        print(f"Handling metapath: {key}" )
        if not file_to_check.exists():
            hg = hintohg.rdf_to_homogeneous(graph, item)
            nx.write_gpickle(hg, data_folder / (key + ".gpickle"))
            print("HG saved in folder \"homogeneous_graphs\"")
        else:
            hg = nx.read_gpickle(data_folder / (key + ".gpickle")) 
            print("HG imported")

        sg_40_10 = dynamic_cd.create_snapshot_graph(hg, 40, 10)
        sg_20_10 = dynamic_cd.create_snapshot_graph(hg, 20, 10)
        sg_10_1 = dynamic_cd.create_snapshot_graph(hg, 10, 5)


        sgs = {'40_10' : sg_40_10,
                '20_10' : sg_20_10,
                '10_1' : sg_10_1}
        theta = 0.3
        name = "Romeyn de Hooghe"
        (dcd_results_init_partition, tc, snapshots, snapshot_times) = dynamic_cd.execute_dcd(sgs)
        dynamic_coms = dynamic_cd.matching(tc, theta)
        res = dynamic_cd.find_dyn_com(dynamic_coms, name, tc, snapshots, snapshot_times)

    # for key, item in metapaths.items():
    #     file_to_check = data_folder / (key + ".gpickle")
    #     print(f"Handling metapath: {key}" )
    #     if not file_to_check.exists():
    #         hg = hintohg.rdf_to_homogeneous(graph, item)
    #         nx.write_gpickle(hg, data_folder / (key + ".gpickle"))
    #         print("HG saved in folder \"homogeneous_graphs\"")
    #     else:
    #         hg = nx.read_gpickle(data_folder / (key + ".gpickle")) 
    #         print("HG imported")

    #     (coms, coms_lcc) = cd.community_detection_louvain(hg)
    #     (formatted_coms, attribute_cache) = cd.format_partition(hg, coms)
    #     cd.export(formatted_coms, key, attribute_cache)




if __name__ == "__main__":
    main()


