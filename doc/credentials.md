# Credentials

There is two ways of authenticating to the MTD's CDS Geospatial data 
infrastructure:

- OAuth2
- API key

## OAuth2

The credentials are retrieved using the device code flow on the first call of 
`teledetection.sign_inplace()`. Just follow the instructions, i.e. click on the 
HTTP link, or scan the QR-code.

The credentials are valid for 5 days. Every time `teledetection.sign_inplace()` 
is called, the credentials are renewed for another 5 days. After 5 days idle, 
you will have to log in again.
If you want something more persistent, or that you can use on several 
computers, you should use an API key.

## API key

API key allow to sign URLs without being authenticated with the single sign on.
Typically, you can use an API key on several machines without having to 
authenticate each time you want to use the SDK.
The SDK can read the API key in two ways:

- From user settings file
- From environment variables

The command line interface (`teledetection`) enables to 
manage API keys.

### From user settings file

Use `teledetection` to register an API key, that will be created and stored into 
your local home directory.

```commandline
tld register
```

Typically on linux the generated API key will be stored in 
`/home/username/.config/teledetection_auth/.apikey`.
Optionally you can override the parent directory setting `TLD_SETTING_DIR`.

Just follow the instructions to log in a single time, then the API key can be used forever on your local computer.
You can duplicate the API key file on other computers.

You can delete the registered API key with:

```commandline
tld delete
```

### From environment variables

You can create a new API key with:

```commandline
tld create
```

!!! Warning

    Note that once created, you won't be able to retrieve the secret key 
    anymore. 

You can then use the access and secret keys setting `TLD_ACCESS_KEY` 
and `TLD_SECRET_KEY`. 

### API key management

List all generated API keys:

```commandline
tld list
```

Revoke a single API key:

```commandline
tld revoke
```

Revoke all generated API keys:

```commandline
tld revoke-all
```

## Signed URLs expiry

The signed URLs for STAC objects assets are valid during 8 hours after 
`teledetection.sign_inplace` is called. 

!!! Info

    `teledetection.sign_inplace()` can also be applied directly on a particular 
    `pystac.item`, `pystac.collection`, `pystac.asset` or any URL as `str`, 
    with the same outcome in term of expiry.

!!! Warning

    Do no confuse credentials validity with images URL token validity.
    Both have different lifecycle. To read how to ask for longer 
    URLs time-to-live, please read the API reference of 
    `teledetection.sign_inplace()`.
