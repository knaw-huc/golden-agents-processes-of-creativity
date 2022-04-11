# Community detection queries
Constructs a list of persons who worked together in different roles: author, contributor, illustrator, or publisher. Based on this dataset: [all-schema-ecartico.ttl](./datasets/stcn/all-schema-ecartico.ttl)

*Endpoint: https://sparql.goldenagents.org/sparql*

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> 
PREFIX schema: <http://schema.org/>

SELECT * WHERE {

    GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/processes_of_creativity_20220128> {

        # There is a book published that has one or more actors involved in the making process
        ?b a schema:Book ;
             schema:author|schema:illustrator|schema:contributor|(schema:publication/schema:publishedBy) ?w1, ?w2 ;
             schema:publication ?publicationEvent .

        ?publicationEvent a schema:PublicationEvent .

        # With an optional begin and end date
        OPTIONAL { ?publicationEvent sem:hasEarliestBeginTimeStamp ?bt} .
        OPTIONAL { ?publicationEvent sem:hasLatestEndTimeStamp ?et} .

        # The relations can be one way (no duplicates)
        FILTER(?w1 != ?w2)
        FILTER(STR(?w1) < STR(?w2))
   }
}
```

## With actor attributes
See also: [query-actor-attributes.md](./query-actor-attributes.md)

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> 
PREFIX schema: <http://schema.org/>

SELECT 
    ?b 
    ?w1 
    ?w2 
    ?bt 
    ?et 
    (GROUP_CONCAT(DISTINCT ?occupationName_w1; SEPARATOR="; ") AS ?w1_occupations) 
    (GROUP_CONCAT(DISTINCT ?occupationName_w2; SEPARATOR="; ") AS ?w2_occupations) 

WHERE {

    GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/processes_of_creativity_20220128> {

    	?b a schema:Book ;
             schema:illustrator|schema:contributor|(schema:publication/schema:publishedBy) ?w1, ?w2 ;
			 schema:publication ?publicationEvent .

		?publicationEvent a schema:PublicationEvent .

		OPTIONAL { ?publicationEvent sem:hasEarliestBeginTimeStamp ?bt} .

		OPTIONAL { ?publicationEvent sem:hasLatestEndTimeStamp ?et} .

		FILTER(?w1 != ?w2)
        FILTER(STR(?w1) < STR(?w2))

	}
  
    OPTIONAL {
        GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
            ?w1 a schema:Person ;
        	    schema:hasOccupation [ a schema:Role ;
                                       schema:hasOccupation ?occupation_w1 ] .
   
            ?occupation_w1 a schema:Occupation ;
                schema:name ?occupationName_w1 .
   
            FILTER(LANG(?occupationName_w1) = 'en')
        }
   }

    OPTIONAL {
        GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
            ?w2 a schema:Person ;
        	    schema:hasOccupation [ a schema:Role ;
                                       schema:hasOccupation ?occupation_w2 ] .
   
            ?occupation_w2 a schema:Occupation ;
                schema:name ?occupationName_w2 .
   
            FILTER(LANG(?occupationName_w2) = 'en')
        }
   }
}
```