# Link the STCN to the Rijksmuseum Research Library. 

## Info
This script queries all Items (cf. WEMI model) in the STCN that have Rijksmuseum 
as holding archive. 

Links to the STCN (by PPN) already exist in the RMLibrary. 
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

### Contact:
* Leon van Wissen (l.vanwissen@uva.nl)
    https://www.goldenagents.org/