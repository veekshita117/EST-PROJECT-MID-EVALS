# GBIF Downloads Registry

Occurrence downloads requested and retrieved via the GBIF Occurrence Download API in `SIMPLE_PARQUET` format.

## Amphibia

- **Group**: Amphibia
- **Download Key**: `0007626-261110092616502`
- **DOI**: [10.15468/dl.46xqsa](https://doi.org/10.15468/dl.46xqsa)
- **Date Created**: 2026-11-14T19:44:48.925+00:00
- **Status**: SUCCEEDED
- **Format**: `SIMPLE_PARQUET`
- **Record Count**: 8,805,881 occurrences
- **Archive Size**: 660,616,974 bytes (630.01 MB)
- **Local Directory**: `GBIF/raw/parquet_amphibia/`
- **Download URL**: https://api.gbif.org/v1/occurrence/download/request/0007626-261110092616502.zip
- **Exact Predicate Query**:
```json
{
  "type": "and",
  "predicates": [
    {
      "type": "equals",
      "key": "CLASS_KEY",
      "value": "131"
    },
    {
      "type": "equals",
      "key": "HAS_COORDINATE",
      "value": "true"
    },
    {
      "type": "equals",
      "key": "HAS_GEOSPATIAL_ISSUE",
      "value": "false"
    },
    {
      "type": "equals",
      "key": "OCCURRENCE_STATUS",
      "value": "PRESENT"
    },
    {
      "type": "isNotNull",
      "parameter": "SPECIES_KEY"
    },
    {
      "type": "greaterThanOrEquals",
      "key": "YEAR",
      "value": "1970"
    },
    {
      "type": "in",
      "key": "BASIS_OF_RECORD",
      "values": [
        "HUMAN_OBSERVATION",
        "PRESERVED_SPECIMEN",
        "MACHINE_OBSERVATION",
        "OBSERVATION"
      ]
    }
  ]
}
```

## Mammalia

- **Group**: Mammalia
- **Download Key**: `0007627-261110092616502`
- **DOI**: [10.15468/dl.yqmpcx](https://doi.org/10.15468/dl.yqmpcx)
- **Date Created**: 2026-11-14T19:44:59.042+00:00
- **Status**: SUCCEEDED
- **Format**: `SIMPLE_PARQUET`
- **Record Count**: 40,334,722 occurrences
- **Archive Size**: 2,371,157,556 bytes (2,261.31 MB)
- **Local Directory**: `GBIF/raw/parquet_mammalia/`
- **Download URL**: https://api.gbif.org/v1/occurrence/download/request/0007627-261110092616502.zip
- **Exact Predicate Query**:
```json
{
  "type": "and",
  "predicates": [
    {
      "type": "equals",
      "key": "CLASS_KEY",
      "value": "359"
    },
    {
      "type": "equals",
      "key": "HAS_COORDINATE",
      "value": "true"
    },
    {
      "type": "equals",
      "key": "HAS_GEOSPATIAL_ISSUE",
      "value": "false"
    },
    {
      "type": "equals",
      "key": "OCCURRENCE_STATUS",
      "value": "PRESENT"
    },
    {
      "type": "isNotNull",
      "parameter": "SPECIES_KEY"
    },
    {
      "type": "greaterThanOrEquals",
      "key": "YEAR",
      "value": "1970"
    },
    {
      "type": "in",
      "key": "BASIS_OF_RECORD",
      "values": [
        "HUMAN_OBSERVATION",
        "PRESERVED_SPECIMEN",
        "MACHINE_OBSERVATION",
        "OBSERVATION"
      ]
    }
  ]
}
```
