"""
This file changes the URIs of the data that was extracted from the Rijksmuseum
Library and STCN datasets to an ECARTICO URI that is more canonical. This way, 
we keep one URI for the same person in all these datasets, without turning on 
sameAs reasoning. 

If no mapping is found to either ECARTICO (preferred) or the NTA, the resource
is removed from the data. We do this for URIs on id.rijksmuseum.nl and the 
self-created data.goldenagents.org/datasets/rmlibrary/person/ URIs. 

This is a method to improve the quality of the data, since the ECARTICO and NTA
datasets are more reliable than the Rijksmuseum Library data. 
"""

import pandas as pd

from rdflib import ConjunctiveGraph, URIRef, RDF


def main(filepath: str, destination: str, mapping_ecartico: str,
         mapping_wikidata: str):

    mapping = dict()
    df = pd.read_csv(mapping_ecartico)
    for i in df.to_dict(orient='records'):
        mapping[i['uri']] = i['ecartico']

    df = pd.read_csv(mapping_wikidata)
    for i in df.to_dict(orient='records'):

        rmid = i['rmid']
        nta = i['nta']

        # already defined
        if rmid in mapping:
            continue
        # prefer ECARTICO
        elif nta in mapping:
            mapping[rmid] = mapping[nta]
        # otherwise NTA
        else:
            mapping[rmid] = nta

    g = ConjunctiveGraph()
    g.parse(filepath, format='turtle')

    # Replace URIs for canonical ECARTICO URIs
    for uri, ecartico in mapping.items():

        uri = URIRef(uri)
        ecartico = URIRef(ecartico)

        for predicate, object in g.predicate_objects(subject=uri):
            g.remove((uri, predicate, object))
            g.add((ecartico, predicate, object))

        for subject, predicate in g.subject_predicates(object=uri):
            g.remove((subject, predicate, uri))
            g.add((subject, predicate, ecartico))

    # Remove everything that was not mapped to ECARTICO or NTA
    subjects = g.subjects(predicate=RDF.type)
    for resource in subjects:
        if 'id.rijksmuseum.nl' in str(resource) or 'data.goldenagents.org/datasets/rmlibrary/person/' in str(resource):
            g.remove((resource, None, None))
            g.remove((None, None, resource))


    g.serialize(destination, format='turtle')


if __name__ == "__main__":

    FILEPATH = 'all-schema.ttl'
    DESTINATION = 'all-schema-ecartico.ttl'

    MAPPING_ECARTICO = 'all-schema-mapping.csv'
    MAPPING_WIKIDATA = 'wikidata-mapping.csv'

    main(FILEPATH, DESTINATION, MAPPING_ECARTICO, MAPPING_WIKIDATA)