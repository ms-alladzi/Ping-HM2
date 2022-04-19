{
    "name"          : "Execute Direct Query",
    "version"       : "1.0",
    "author"        : "-",
    "website"       : "-",
    "category"      : "Extra Tools",
    "license"       : "LGPL-3",
    "support"       : "-",
    "summary"       : "Execute query from database",
    "description"   : """
        Execute query without open postgres
Goto : Settings > Technical
    """,
    "depends"       : [
        "base",
        "mail",
    ],
    "data"          : [
        "views/ms_query_view.xml",
        "security/ir.model.access.csv",
    ],
    "demo"          : [],
    "test"          : [],
    "qweb"          : [],
    "css"           : [],
    "application"   : True,
    "installable"   : True,
    "auto_install"  : False,
}