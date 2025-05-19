# Authentication

There are two ways to authenticate to the MTD's CDS Geospatial data infrastructure:
- OAuth2
- API key

## OAuth2

Credentials are retrieved using the device code flow on the first use of `teledetection` (from Python or the command line interface). An authentication link is displayed to enable single sign-on. Once logged in or reused, the OAuth2 credentials are valid for a few hours. After expiry, you will have to log in again. If you want something more persistent or that you can use on several computers, you should use an API key.
## API key

API keys allow to sign URLs without being authenticated with the single sign-on. Typically, you can use an API key on several machines without having to authenticate each time you want to use the SDK. The SDK can read the API key in two ways:
- From user settings file
- From environment variables

The command line (`tld apikey`) enables to manage API keys.

### From user settings file

Use `tld` to register an API key, which will be created and stored in your local home directory:
```commandline
tld apikey register
```

You can add an optional description to the new key:

```commandline
tld apikey register "This is my new key 1234"
```

Typically on linux the generated API key will be stored in 
`/home/username/.config/teledetection_auth/.apikey`.
Optionally you can override the parent directory setting `TLD_SETTING_DIR`.

Just follow the instructions to log in a single time, then the API key can be 
used forever on your local computer.
You can duplicate the API key file on other computers.

You can delete the registered API key with:

```commandline
tld apikey remove
```

### From environment variables

You can create a new API key with:

```commandline
tld apikey create
```

!!! Warning

    Note that once created, you won't be able to retrieve the secret key 
    anymore. 

You can then use the access and secret keys setting `TLD_ACCESS_KEY` 
and `TLD_SECRET_KEY`. 

### API key management

List all generated API keys:

```commandline
tld apikey list
```

Revoke a single API key, e.g. `l9ddddddUU04aGjmS`:

```commandline
tld apikey revoke l9ddddddUU04aGjmS
```

Revoke all generated API keys:

```commandline
tld apikey revoke-all
```

!!! Note

    You can also use your web browser to manage your API keys 
    [here](https://gate.stac.teledetection.fr)
