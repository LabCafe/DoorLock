import os
from pyairtable import Table

api_key = "keyjl2WnFe7ASauCP"
table = Table(api_key, 'app3OY1pHBgeuPezj', 'tbllvRdtsRWeO21H1')
for record in table.all():
  print(record["fields"]["Email"])