import requests

API_KEY = "oK/SXE39wQjLsyLhR8Sy8DYniOLa5Z1+"

resp = requests.get(
    "https://marsapi.ams.usda.gov/services/v1.2/reports/BH_FV020/report details",
    auth=(API_KEY, ""),
    params={"q": 'commodity="Peppers, Bell Type";report_begin_date=07/01/2024:08/01/2024'},
    timeout=15,
)
print(resp.status_code)
print(resp.text[:800])