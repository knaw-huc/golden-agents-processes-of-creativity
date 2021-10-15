import pandas as pd

from rdflib import ConjunctiveGraph
from rdflib.term import URIRef


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
    g.parse(filepath)

    for uri, ecartico in mapping.items():

        uri = URIRef(uri)
        ecartico = URIRef(ecartico)

        for predicate, object in g.predicate_objects(subject=uri):
            g.remove((uri, predicate, object))
            g.add((ecartico, predicate, object))

        for subject, predicate in g.subject_predicates(object=uri):
            g.remove((subject, predicate, uri))
            g.add((subject, predicate, ecartico))

    g.serialize(destination, format='turtle')


if __name__ == "__main__":

    FILEPATH = 'all-schema.ttl'
    DESTINATION = 'all-schema-ecartico.ttl'

    MAPPING_ECARTICO = 'all-schema-mapping.csv'
    MAPPING_WIKIDATA = 'wikidata-mapping.csv'

    main(FILEPATH, DESTINATION, MAPPING_ECARTICO, MAPPING_WIKIDATA)