# Rerunner

Microservice that schedules a new rescoring on modified pedigree files on a remote machine. The service creates new pedigree and run data files based on input recieved through the exposed API.

## API Documentation

You can run a pedigree rescoring through an included REST-api (openapi v3). The API documentation is accessable on the url <service_url>:<service_port>/v1.0/ui/.

## Setup

Rerunner transfers the novel pedigree and run data files to a remote server where it also initiates a recalculation of the scores.
It uses ssh keys to authenticate itself on remote. SSH keys are mounted to the image during startup [docker secrets](https://docs.docker.com/engine/swarm/secrets/).

``` yaml
secrets:
  id_rsa:
    file: containers/rerunner/auth/id_rsa  # private key of user
```

### Configuration

The service is configured through a combination of a `config.yml`,located in the parent directory, file and environmental variables. 
Non-sensitive information are stored in the config file so it can be versioned.

``` yaml
# database connection
MONGO_HOST: db  # default localhost
MONGO_PORT: 27017  # default 27017
MONGO_DBNAME: scout  # default scout
MONGO_USERNAME:  # default None
MONGO_PASSWORD:  # default None
# remote and data transfer
WORKFLOW_HOST: rs-fe1  # host
WORKFLOW_PATH:  # /path/to/workflow.nf
WORKFLOW_DATA_DIR:  # /path/to/data
```

Sensitive configurations are set through environmental varialbes. The passphrase of the SSH keys can be specified wuth the varialbe `SSH_PASSPHRASE`. You can specifiy the names of the SSH key to be used for copying and running commands on the remote with the varible `SSH_KEY_FILENAME`.

