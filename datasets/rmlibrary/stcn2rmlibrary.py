"""
Link the STCN to the Rijksmuseum Research Library. 

This script queries all Items (cf. WEMI model) in the STCN that have Rijksmuseum 
as holding archive. Links to the STCN (by PPN) already exist in the RMLibrary. 
Fetch them using their SRU API (https://data.rijksmuseum.nl/bibliographic-data/api/)
that returns MARC21lite records. 

Data is saved to text/turtle (.ttl) and is modelled in schema.org in the same 
fashion as the STCN.

Two URIs are generated if there are no identifiers available at the Rijksmuseum
Libary so that they can be reconciled later on:

    1. Persons (authors/contributors): https://data.goldenagents.org/datasets/rmlibrary/person/"
    2. Organizations (printers/publishers): https://data.goldenagents.org/datasets/rmlibrary/organization/"

OOP approach built upon an adapted version of RDFAlchemy for Python (3.7). 
Install with:

    ```bash
    pip install git+https://github.com/LvanWissen/RDFAlchemy.git
    ```

Contact:
    Leon van Wissen (l.vanwissen@uva.nl)
    https://www.goldenagents.org/

"""

import io
import uuid
from xml.etree import ElementTree

import requests

import pymarc

from rdflib import (
    ConjunctiveGraph,
    Namespace,
    OWL,
    Literal,
    URIRef,
    BNode,
    XSD,
    RDFS,
    RDF,
)
from rdfalchemy import rdfSubject, rdfSingle, rdfMultiple

bio = Namespace("http://purl.org/vocab/bio/0.1/")
schema = Namespace("https://schema.org/")
sem = Namespace("http://semanticweb.cs.vu.nl/2009/11/sem/")
pnv = Namespace("https://w3id.org/pnv#")

##############
# Data model #
##############


class Thing(rdfSubject):
    rdf_type = None

    label = rdfMultiple(RDFS.label)
    comment = rdfSingle(RDFS.comment)

    name = rdfMultiple(schema.name)
    description = rdfMultiple(schema.description)

    sameAs = rdfMultiple(OWL.sameAs)
    schemaSameAs = rdfMultiple(schema.sameAs)
    isPartOf = rdfSingle(schema.isPartOf)
    license = rdfSingle(schema.license)
    publisher = rdfSingle(schema.publisher)

    mainEntityOfPage = rdfSingle(schema.mainEntityOfPage)

    dateCreated = rdfSingle(schema.dateCreated)
    dateModified = rdfSingle(schema.dateModified)

    subjectOf = rdfMultiple(schema.subjectOf)

    value = rdfSingle(RDF.value)

    startDate = rdfSingle(schema.startDate)
    hasTimeStamp = rdfSingle(sem.hasTimeStamp)
    hasBeginTimeStamp = rdfSingle(sem.hasBeginTimeStamp)
    hasEndTimeStamp = rdfSingle(sem.hasEndTimeStamp)
    hasEarliestBeginTimeStamp = rdfSingle(sem.hasEarliestBeginTimeStamp)
    hasLatestBeginTimeStamp = rdfSingle(sem.hasLatestBeginTimeStamp)
    hasEarliestEndTimeStamp = rdfSingle(sem.hasEarliestEndTimeStamp)
    hasLatestEndTimeStamp = rdfSingle(sem.hasLatestEndTimeStamp)


class Book(Thing):
    rdf_type = schema.CreativeWork, schema.Book, schema.ProductModel

    author = rdfMultiple(schema.author)
    contributor = rdfMultiple(schema.contributor)
    inLanguage = rdfMultiple(schema.inLanguage)
    publication = rdfSingle(schema.publication)

    about = rdfMultiple(schema.about)

    numberOfPages = rdfSingle(schema.numberOfPages)

    workExample = rdfMultiple(schema.workExample)


class BookItem(Book):
    rdf_type = (
        schema.CreativeWork,
        schema.Book,
        schema.IndividualProduct,
        schema.ArchiveComponent,
    )

    itemLocation = rdfMultiple(schema.itemLocation)
    holdingArchive = rdfSingle(schema.holdingArchive)
    exampleOfWork = rdfSingle(schema.exampleOfWork)


class Role(Thing):
    rdf_type = schema.Role
    author = rdfMultiple(schema.author)
    contributor = rdfMultiple(schema.contributor)
    about = rdfSingle(schema.about)
    roleName = rdfSingle(schema.roleName)
    publishedBy = rdfSingle(schema.publishedBy)
    hasName = rdfMultiple(pnv.hasName)


class Person(Thing):
    rdf_type = schema.Person

    hasName = rdfMultiple(pnv.hasName)
    gender = rdfSingle(schema.gender)


class Organization(Thing):
    rdf_type = schema.Organization

    hasName = rdfMultiple(pnv.hasName)


class PublicationEvent(Thing):
    rdf_type = schema.PublicationEvent

    publishedBy = rdfMultiple(schema.publishedBy)
    location = rdfSingle(schema.location)


class Document(Thing):
    rdf_type = schema.WebPage, schema.Dataset

    mainEntity = rdfSingle(schema.mainEntity)

    identifier = rdfMultiple(schema.identifier)


class PropertyValue(Thing):
    rdf_type = schema.PropertyValue

    value = rdfSingle(schema.value)


class Place(Thing):
    rdf_type = schema.Place


#############
# Functions #
#############


def unique(*args, ns=None):
    """
    Get a unique identifier (BNode or URIRef) for an entity based on an ordered
    list of objects. Specify the namespace (ns) attribute to return a URIRef. 

    The uuid5 module is used to generate a unique identifier based on the 
    concatenation of string representations of the objects given to this 
    function. This way, every (unique) combination of objects will result in 
    the same unique identifier. Used instead of messing with mapping 
    dictionaries and string normalization.

    Args:
        *args: Variable length argument list of objects.
        ns (str, optional): If given, return a URIRef on this namespace. Otherwise, return a BNode.
    
    Returns:
        A BNode or URIRef.
    """

    identifier = "".join(str(i) for i in args)  # order matters

    unique_id = uuid.uuid5(uuid.NAMESPACE_X500, identifier)

    if ns:
        return URIRef(ns + str(unique_id))
    else:
        return BNode(unique_id)


def getSTCNBooks(ENDPOINT: str = "http://data.bibliotheken.nl/sparql"):
    """
    Get all books (Manifestations) from the STCN collection that have 
    "Rijksmuseum" as holding archive.

    Args:
        ENDPOINT (str, optional): SPARQL endpoint
    """

    q = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <https://schema.org/>

    SELECT DISTINCT ?book ?title WHERE {
    ?book a schema:Book ;
            schema:name ?title .
    
    ?item a schema:IndividualProduct ;
            schema:exampleOfWork ?book ;
            # schema:itemLocation ?shelfmark ;
            schema:holdingArchive ?archive .
    
    FILTER(CONTAINS(?archive, "Rijksmuseum"))
    }
    """

    headers = {"Accept": "application/sparql-results+json"}
    params = {"query": q}
    r = requests.get(ENDPOINT, headers=headers, params=params)
    data = r.json()

    books = []
    for r in data["results"]["bindings"]:
        record = dict()
        for k, v in r.items():
            record[k] = v["value"]
        books.append(record)

    return books


def getSTCNItem(
    itemLocations: list,
    holdingArchive: str = "Amsterdam, Rijksmuseum Research Library",
    ENDPOINT: str = "http://data.bibliotheken.nl/sparql",
):
    """
    Find the STCN item for a given itemLocation and holdingArchive.

    Args:
        itemLocations (list): The itemLocations of the item to search for.
        holdingArchive (str, optional): The holdingArchive of the item to search for.
        ENDPOINT (str, optional): The SPARQL endpoint to use.
    
    Returns:
        List of dicts with with items    
    """

    books = []
    for itemLocation in itemLocations:

        q = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>

        SELECT * WHERE {{
        ?book a schema:IndividualProduct ;
                schema:itemLocation ?shelfmark ;
                schema:holdingArchive ?archive .
        
        FILTER(?shelfmark = "{itemLocation}")
        FILTER(CONTAINS(?archive, "{holdingArchive}"))
        }}
        """

        headers = {"Accept": "application/sparql-results+json"}
        params = {"query": q}
        r = requests.get(ENDPOINT, headers=headers, params=params)
        data = r.json()

        for r in data["results"]["bindings"]:
            record = dict()
            for k, v in r.items():
                record[k] = v["value"]
            books.append(record)

    return books


def getRMLibraryBook(
    stcnURI: str,
    stcnTitle: str = "",
    ENDPOINT: str = "http://library.rijksmuseum.nl:9998/biblios",
):
    """
    Get a book from the Rijksmuseum Library API. The PPN in the STCN URI is 
    used as search parameter. 

    Args:
        stcnURI (str): URI of the book in the STCN
        stcnTitle (str, optional): Title of the book in the STCN
        ENDPOINT (str, optional): endpoint of the Rijksmuseum Library API

    """

    ppn = stcnURI.replace("http://data.bibliotheken.nl/id/nbt/p", "")

    params = {
        "version": "1.1",
        "operation": "searchRetrieve",
        "maximumRecords": 20,
        "query": ppn,
    }
    r = requests.get(ENDPOINT, params=params)

    ElementTree.register_namespace("", "http://www.loc.gov/MARC21/slim")
    tree = ElementTree.fromstring(r.content)

    for el in tree.findall(
        ".//marc21slim:record",
        namespaces={
            "zs": "http://www.loc.gov/zing/srw/",
            "marc21slim": "http://www.loc.gov/MARC21/slim",
        },
    ):

        f = io.BytesIO(ElementTree.tostring(el, encoding="utf-8"))
        marc_records = pymarc.parse_xml_to_array(f)

        for record in marc_records:

            uri = record["024"]["a"]
            name = record.title()
            shelfmarks = [i["o"] for i in record.get_fields("952") if i["o"]]
            ocolc_id = record["035"]["a"].replace("(OCoLC)", "")

            comments = []
            for commentField in record.get_fields("500"):
                comments.append(commentField["a"])

            ocolc = URIRef("http://www.worldcat.org/oclc/" + ocolc_id)

            stcnManifestation = Book(
                URIRef("http://data.bibliotheken.nl/id/nbt/p" + ppn),
                name=[stcnTitle] if stcnTitle else [],
                schemaSameAs=[ocolc],
            )

            book = BookItem(
                URIRef(uri),
                name=[name],
                itemLocation=shelfmarks,
                holdingArchive="Amsterdam, Rijksmuseum Research Library",
                exampleOfWork=stcnManifestation,
                description=comments,
            )

            stcn_items = getSTCNItem(shelfmarks)
            if len(stcn_items) >= 1:
                book.sameAs = [URIRef(i["book"]) for i in stcn_items]

            authors = getPersons(record, field="100", property="author")
            contributors = getPersons(record, field="700", property="contributor")

            book.author = authors
            book.contributor = contributors

            # Only remove the period from the end of the name, there is no point
            # in correcting all the messy dates, as the STCN already structured them properly.

            if record["260"]:

                startDate = record["260"]["c"]
                if startDate and startDate.endswith("."):
                    startDate = startDate[:-1]

                organizationName = record["260"]["b"]
                if organizationName and organizationName.endswith(","):
                    organizationName = [organizationName[:-1]]
                elif organizationName:
                    organizationName = [organizationName]
                else:
                    organizationName = []

                location = record["260"]["a"]
                if location and location.endswith(","):
                    location = location[:-1]

                pubEvent = PublicationEvent(
                    BNode(uri + "#publication"),
                    location=location,
                    publishedBy=[
                        Organization(
                            unique(
                                uri,
                                "organization",
                                record["260"]["b"],
                                ns="https://data.goldenagents.org/datasets/rmlibrary/organization/",
                            ),
                            name=organizationName,
                        )
                    ],
                    startDate=startDate,
                )
                book.publication = pubEvent


def getPersons(record, field, property):
    """
    Get all persons (e.g. authors or contributors) from a MARC21 record.

    Args:
        record (pymarc.Record): MARC21 record
        field (str): MARC field to search for
        property (str): schema property to model in the Role (author or contributor)
    
    Returns:
        List of Role objects
    """

    recordURI = record["024"]["a"]

    roles = []
    for fieldEntry in record.get_fields(field):

        name = fieldEntry["a"]

        if name and name.endswith(","):
            name = name[:-1]

        roleName = fieldEntry["e"]

        if fieldEntry["9"] not in ("0", None):
            uri = URIRef("https://id.rijksmuseum.nl/310" + fieldEntry["9"])
        else:
            uri = unique(
                recordURI,
                "person",
                name,
                ns="https://data.goldenagents.org/datasets/rmlibrary/person/",
            )

        # A nice label for the role resource
        roleNameLiteral = (
            [Literal(f"{name} ({roleName})", lang="nl")]
            if roleName
            else [Literal(name, lang="nl")]
        )

        person = Person(uri, name=[name])
        role = Role(
            unique(recordURI, uri, property, roleName),
            roleName=roleName,
            name=roleNameLiteral,
        )

        # Add author or contributor property
        setattr(role, property, [person])

        roles.append(role)

    return roles


if __name__ == "__main__":

    g = rdfSubject.db = ConjunctiveGraph()
    g.bind("schema", schema)
    g.bind("owl", OWL)

    # Fetch books from KB endpoint
    books = getSTCNBooks()
    print(f"Found {len(books)} books with an item in RM Library!")

    # Find their equivalent book in RMLibrary
    for n, book in enumerate(books, 1):

        print(f"Book {n} of {len(books)}", end="\r")
        getRMLibraryBook(book["book"], book["title"])

    # Serialize the graph
    g.serialize("ga_stcn_rmlibrary.ttl", format="turtle")
    print("Saved to ga_stcn_rmlibrary.ttl")
