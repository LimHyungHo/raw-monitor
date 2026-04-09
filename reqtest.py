import requests

url = "http://www.law.go.kr/DRF/lawSearch.do"

params = {
    "OC": "ITIBKI",
    "target": "law",
    "query": "전자금융거래법",
    "type": "JSON"
}

# params = {
#     "OC": "ITIBKI",
#     "target": "admrul",
#     "query": "전자금융감독규정",
#     "type": "JSON"
# }

res = requests.get(url, params=params)
print(res.text)