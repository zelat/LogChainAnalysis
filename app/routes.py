from flask import Flask, render_template, request, jsonify
from app import app
import json
from utils import esData


@app.route('/', methods=("GET", "POST"))
def index():
    if request.method == "POST":
        log_info = request.form.to_dict()
        uuid = log_info.get("uuid")
        date = log_info.get("date").replace("-", ".")
    else:
        uuid = "7cc17533-e585-4df4-8f70-dc21b0cbff93"
        date = "2021.03.15"
    resource_index = "resource-log-" + date
    obj = esData.ElasticObj("_doc")
    index_List = list(obj.indices.get_alias('*-log-' + date).keys())
    index_List.remove(resource_index)
    mappingDict = obj.getMappingByResource(resource_index, index_List, uuid, date, 10)
    response = json.dumps(mappingDict, sort_keys=True, indent=4, separators=(',', ': '))
    return render_template("index.html", response=response)

@app.route('/detailLog', methods=['POST'])
def detailLog():
    obj = esData.ElasticObj("_doc")
    data = request.get_json()
    index = data['index']
    request_id = data['request_id']
    jsonData = json.dumps(obj.getLog(index_name=index, request_id=request_id))
    return  jsonify(jsonData)


