# Policies

The *Maison de la Teledetection* STAC API is transactionnal: any user 
can push STAC objects to the API. On the other end, the signing URLs 
API allows to upload files to the servers. 

To be able to push STAC objects and files, a policy must be defined for 
the user to allow the operations on the `collections` (for STAC) and 
`storages` (for files) resources, in 
[this repository](https://forge.inrae.fr/teledec/gdc-policies).

To request the required permissions, the user can perform a 
[merge request](https://docs.gitlab.com/ee/user/project/merge_requests/) 
, to modify the `policies.yaml` file of the repository.

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
