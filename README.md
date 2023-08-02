# <center><font color=green size=10>PilotScope</font></center>

PilotScope is an AI4DB deployment tool. The ML methods in PilotScope could apply several abstracted operators to interact with databases to fulfill their functions. We now support 15 ML methods、2 DBs and 11 push-and-pulls. And here is the source code of "PilotScope: Steering Databases with Machine Learning Drivers". You can get the PostgreSQL's source code with pilotscope patch and the Spark's source code with pilotscope patch from [PostgresSQL repo](https://github.com/duoyw/PilotScopePostgreSQL) and [Spark repo](https://github.com/duoyw/PilotScopeSpark) respectively.

<!-- wait  for tutorial-->
A detailed tutorial will be provided on : [tutorial]()

| [Code Structure](#code-structure) | [Quick Start](#quick-start) | [Advanced](#advanced) | [Contributing](#contributing) | 

<!-- ## News -->
## Code Structure
```
PilotScope/
├── cacheData                               
├── common                                  # Useful tools for PilotScope
│   ├── Cache.py
│   ├── dotDrawer.py
│   ├── ...
├── components                              
│   ├── Anchor                              # Base anchors and implementation of specific anchors       
│   │   ├── BaseAnchor
│   │   ├── AnchorTransData.py
│   │   ├── ...
│   ├── Dao                                 # Management of user's data and training data
│   │   ├── PilotTrainDataManager.py
│   │   └── PilotUserDataManager.py
│   ├── DataFetcher                         # Details of the entire process about fetching data. 
│   │   ├── BaseDataFetcher.py
│   │   ├── HttpDataFetch.py
│   │   ├── PilotCommentCreator.py
│   │   └── PilotStateManager.py
│   ├── DBController                        # Base controllers of DB and implementation of specific controllers
│   │   ├── BaseDBController.py
│   │   ├── PostgreSQLController.py
│   │   └── SparkSQLController.py
│   ├── Exception                           # Some exception which may occur in the lifecycle of pilotscope
│   │   └── Exception.py
│   ├── Factory                             # Factory patterns
│   │   ├── AnchorHandlerFactory.py
│   │   ├── DataFetchFactory.py
│   │   ├── ...
│   ├── PilotConfig.py                      # Configurations for specific databases
│   ├── PilotEnum.py                        # Enumeration types
│   ├── PilotEvent.py                       # Base events of pilotscope
│   ├── PilotModel.py                       # Base models of pilotscope
│   ├── PilotScheduler.py                   # Sheduling data traing、inference、collection push-and-pull and so on
│   ├── PilotSysConfig.py                   # Configuration for data collection and storage
│   ├── PilotTransData.py                   # Parsing and storing data
│   └── Server                              # HTTP server for receiving data
│       └── Server.py                       
├── examples                                # Examples of some tasks and models
└── test                                    # Unittests of PilotScope
```
## Quick Start
We choose PostgreSQL as the base database. The following are some necessary steps to use PilotScope on it:
1. Installation

```bash
# 1. download the PostgreSQL 13.1  
wget https://ftp.postgresql.org/pub/source/v13.1/postgresql-13.1.tar.bz2
tar -xvf postgresql-13.1.tar.bz2

# 2. install PostgreSQL
make
make install

# 3. modify the configuration of PostgreSQL in postgresql.conf
listen_addresses = '*'
log_min_messages = info
shared_preload_libraries = 'pilotscope'

# 4. modify the configuration of PostgreSQL in pg_hba.conf
host all all all md5

# 5. install the pilotscope extension
git clone https://github.com/duoyw/PilotScopePostgreSQL.git
cd PilotScopePostgreSQL
sh install_pilotscope.sh
pg_ctl -D data restart
```

2. Load dataset into database
   You can get imdb、stats、tpc-h and other public datasets with relative workload on the Internet. And then you should load the dataset into database. Here we omit this step.

3. Environment
```bash
# some packages used by PilotScope
pip3 -r requirements.txt
``` 

4. Run
```bash
# run some tests in 'test/'
python3 -m unittest test_bao_example.py
python3 -m unittest test_knob_example.py
...
```

## Extension
As an middleware system, PilotScope can support to deploy any ML method on any native database and it can be easily extended to support a variety of AI4DB tasks 、algorithms and databases. We will support more of them in the future and build an open-source community, which will accelerate the iteration of ML methods in research community and make AI4DB truly appliable in production scenarios.
## Documentation
The classes and methods of PilotScope will be documented and we plan to put the documentation in this repository in the future.
<!-- ## License
## Publications -->
## Contributing
As an open-sourced project, we greatly appreciate any contribution to PilotScope! 