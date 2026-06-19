# Policies

The *Maison de la Teledetection* STAC API is transactionnal: any user 
can push STAC objects to the API. On the other end, the signing URLs 
API allows to upload files to the servers. 

To be able to push STAC objects and files, a policy must be defined for 
the user to allow the operations on the `collections` (for STAC) and 
`storages` (for files) resources, in 
[this repository](https://forge.inrae.fr/teledec/gdc-policies).

To request the modification of policies, the user must perform a 
[merge request](https://docs.gitlab.com/ee/user/project/merge_requests/) 
to modify the 
[`policies.yaml`](https://forge.inrae.fr/teledec/gdc-policies/-/blob/main/policies.yaml?ref_type=heads) 
file. Two ways to do that:

1. Fork the repository, then submit a MR from your fork: this is the traditional 
workflow, as it is done commonly to contribute to external open-source projects. This 
is appropriate for unfrequent modifications of the policies.
2. Request the access to the `gdc-policies` repository as developer, in order
to be able to submit MRs directly to the policies: this is
recommended for frequent modifications of the policies.


!!! tip

    You can find your username:
    
    - on [gate](https://gate.stac.teledetection.fr)
    - or by typing `teledetection.get_username()` in a Python shell

## Example of `policies.yaml`

```yaml
rules:
- user: user_name
  collections:
  - nom-collection-1
  - nom-collection-2
  storages:
  - https://s3-data.meso.umontpellier.fr/bucket1/prefixe1
  - https://s3-data.meso.umontpellier.fr/bucket1/prefixe2
  - https://s3-data.meso.umontpellier.fr/bucket2

```

Note that `collections` and `storages` are completely independent.
