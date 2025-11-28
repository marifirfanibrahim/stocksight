Stocksight/
│
├── app.py                    # main gui application
├── run.py                    # application runner with checks
├── build.py                  # build script for executable
├── config.py                 # configuration settings
├── requirements.txt          # dependencies
├── README.md                 # documentation
├── .gitignore               # git ignore patterns
│
├── data/                     # datasets
│   └── inventory.csv         # sample data
│
├── output/                   # generated files
│   └── (forecast files)
│
└── utils/                    # utility modules
    ├── __init__.py           # package init
    ├── preprocessing.py      # data cleaning
    ├── forecasting.py        # model helpers
    ├── visualization.py      # chart generation
    └── reporting.py          # report generation