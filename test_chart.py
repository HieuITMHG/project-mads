from api.utils.chart_parser import extract_valid_json
import json

s = """{"data":[{"customdata":[["credit_card"],["boleto"],["voucher"],["debit_card"],["not_defined"]],"domain":{"x":[0.0,1.0],"y":[0.0,1.0]},"hole":0.3,"hovertemplate":"payment_type=%{customdata[0]}<br>payment_count=%{value}<extra></extra>","labels":["credit_card","boleto","voucher","debit_card","not_defined"],"legendgroup":"","marker":{"colors":["#1F77B4","#FF7F0E","#2CA02C","#D62728","#9467BD"]},"name":"","showlegend":true,"values":{"dtype":"i4","bdata":"+ysBAEhNAACPFgAA+QUAAAMAAAA="},"type":"pie"}],"layout":{"template":{"data":{"scatter":[{"type":"scatter"}]},"legend":{"tracegroupgap":0},"title":{"text":"Distribution of Payment Types"}}}}"""

try:
    e = extract_valid_json(s)
    print("EXTRACTED:", e)
    json.loads(e)
    print("SUCCESS!")
except Exception as e:
    print("JSONDecodeError:", e)
