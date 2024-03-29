# Example queries to fetch attributes on persons from ECARTICO 

*Endpoint: https://sparql.goldenagents.org/sparql*

## Birth place

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>

SELECT * WHERE {

  GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
    ?person a schema:Person ;
        schema:birthPlace ?birthPlace .
   
    ?birthPlace a schema:Place ;
        schema:name ?birthPlaceName .
  }
 
}
```

## Birth date

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>

SELECT * WHERE {

  {
  GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
    ?person a schema:Person ;
        schema:birthDate ?birthDate .
        
    FILTER(!(ISURI(?birthDate)))
    
    }
  }
  UNION {
    GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
      ?person a schema:Person ;
         schema:birthDate [ a schema:StructuredValue ;
                            rdf:value ?birthDate ] .
      }
    }
 
}


```

## Religion

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>
PREFIX ecartico: <https://www.vondel.humanities.uva.nl/ecartico/lod/vocab/#>

SELECT * WHERE {

  GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
    ?person a schema:Person ;
        ecartico:religion ?religionName .
  }
 
}

```

## Occupation

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>

SELECT * WHERE {

  GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
    ?person a schema:Person ;
        schema:hasOccupation [ a schema:Role ;
                               schema:hasOccupation ?occupation ] .
   
    ?occupation a schema:Occupation ;
        schema:name ?occupationName .
   
    FILTER(LANG(?occupationName) = 'en')
   
  }
 
}

```

## Occupational address

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>

SELECT * WHERE {

  GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
    ?person a schema:Person ;
        schema:workLocation ?workLocationRole .
    
    ?workLocationRole a schema:Role ;
        schema:workLocation ?workLocation .
    
    ?workLocation a schema:Place ;
        schema:name ?workLocationName .
    
    OPTIONAL { ?workLocationRole schema:startDate ?startDate . }
    OPTIONAL { ?workLocationRole schema:endDate ?endDate . }

   
  }
 
}
```

## Family relations

```sparql
PREFIX bio: <http://purl.org/vocab/bio/0.1/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>

SELECT * WHERE {

  GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
    ?person a schema:Person .
    
    OPTIONAL { ?person schema:parent ?parent . }
    OPTIONAL { ?person schema:children ?child . }
    
    OPTIONAL { ?person schema:spouse ?spouse . } 
    
    }      
  
}

```

## Business relations (WIP)

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>
PREFIX ecartico: <https://www.vondel.humanities.uva.nl/ecartico/lod/vocab/#>

SELECT * WHERE {

  GRAPH <https://data.goldenagents.org/datasets/u692bc364e9d7fa97b3510c6c0c8f2bb9a0e5123b/ecartico_20211014> {
    ?person a schema:Person ;
  		  ?relation [ a schema:Role ;
                    ?relation ?relatedPerson ] .
      
    ?relatedPerson a schema:Person .
  		
    ?relation rdfs:subPropertyOf ecartico:hasRelationWith .
    
    }      
  
}
```



