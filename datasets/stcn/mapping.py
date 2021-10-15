import pandas as pd

from rdflib import ConjunctiveGraph
from rdflib.term import URIRef


def main(filepath: str, destination: str, mappingfile: str):

    df = pd.read_csv(mappingfile)

    mapping = dict()
    for i in df.to_dict(orient='records'):
        mapping[i['uri']] = i['ecartico']

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

    MAPPINGFILE = 'all-schema-mapping.csv'

    main(FILEPATH, DESTINATION, MAPPINGFILE)